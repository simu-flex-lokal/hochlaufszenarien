"""io/infdb_saturation.py — Dachpotenzial C_hi aus der InfDB.

Gleiche Datenbasis und gleiche Regel wie AP 2 (ObjectTypeGenerator), auf denselben Gebäuden, aus denen pylovo
die Netze baut: bewohnte Wohngebäude aus ``basedata.buildings`` (``building_type`` gesetzt, ``occupants`` > 0).
Dachpotenzial je Gebäude [kWp]:

  1. Solarkataster NRW (``opendata.solarkataster_pv_dach``, geladen mit ``db/import_solarkataster.py``):
     Σ installierbare Leistung der Dachteilflächen. In einer importierten Gemeinde hat ein Gebäude ohne
     Dachteilfläche kein geeignetes Dach (0 kWp).
  2. sonst LoD2-Dachfläche × nutzbarer Anteil × kWp/m² (``basedata.building_surface_area``).

    C_hi [kWp] = Σ_Gebäude Dachpotenzial

Regel und Faktoren müssen mit AP 2 übereinstimmen (``technology_sizing.roof_pv_potential_kwp``,
``SizingSettings``), sonst passen die Summe der Gebäude-Potenziale (AP 2) und die Sättigung (AP 3.1) nicht zusammen.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

DEFAULT_DSN = "postgresql://infdb_user:infdb@127.0.0.1:54328/infdb"
ROOF_USABLE_FRACTION = 0.4  # = objecttypegenerator SizingSettings.pv_roof_usable_fraction
KWP_PER_M2 = 0.205          # = objecttypegenerator SizingSettings.pv_kwp_per_m2
IMPLAUSIBLE_ROOF_M2 = 5_000.0  # nur Hinweis: so große Dächer bei Wohngebäuden deuten auf fehlerhafte Geometrie

_BUILDINGS = """
FROM basedata.buildings b
LEFT JOIN (SELECT building_objectid, SUM(area) AS roof_area_m2
           FROM basedata.building_surface_area
           WHERE classname = 'RoofSurface'
           GROUP BY building_objectid) r ON r.building_objectid = b.objectid
{cadastre_join}
WHERE b.gemeindeschluessel = %(ags)s
  AND b.building_type IS NOT NULL
  AND COALESCE(b.occupants, 0) > 0
"""
_CADASTRE_JOIN = """LEFT JOIN (SELECT objectid, SUM(kw) AS kwp
           FROM opendata.solarkataster_pv_dach
           WHERE objectid IN (SELECT objectid FROM basedata.buildings WHERE gemeindeschluessel = %(ags)s)
           GROUP BY objectid) k ON k.objectid = b.objectid"""
ROOF_SQL_WITH_CADASTRE = ("SELECT b.objectid, COALESCE(r.roof_area_m2, 0), k.kwp"
                          + _BUILDINGS.format(cadastre_join=_CADASTRE_JOIN))
ROOF_SQL = "SELECT b.objectid, COALESCE(r.roof_area_m2, 0), NULL::float8" + _BUILDINGS.format(cadastre_join="")
CADASTRE_IMPORTED_SQL = """
SELECT EXISTS (SELECT 1 FROM opendata.solarkataster_pv_import WHERE gemeindeschluessel = %(ags)s)
"""
CADASTRE_TABLES_SQL = """
SELECT to_regclass('opendata.solarkataster_pv_dach') IS NOT NULL
   AND to_regclass('opendata.solarkataster_pv_import') IS NOT NULL
"""


@dataclass(frozen=True)
class RoofPotential:
    ags: str
    buildings: int
    source: str              # "solarkataster" oder "dachflaeche"
    without_suitable_roof: int
    roof_area_m2: float
    c_hi_kwp: float
    c_hi_from_roof_area_kwp: float  # zum Vergleich: Formel über die LoD2-Dachfläche
    implausible: int  # Wohngebäude mit Dach > IMPLAUSIBLE_ROOF_M2

    def summary(self) -> str:
        if self.source == "solarkataster":
            text = (f"InfDB {self.ags}: {self.buildings} Wohngebäude, Solarkataster NRW → C_hi = "
                    f"{self.c_hi_kwp / 1e3:.1f} MWp ({self.without_suitable_roof} ohne geeignetes Dach; "
                    f"Formel über Dachfläche wäre {self.c_hi_from_roof_area_kwp / 1e3:.1f} MWp)")
        else:
            text = (f"InfDB {self.ags}: {self.buildings} Wohngebäude, Dachfläche {self.roof_area_m2 / 1e3:.0f} Tsd. "
                    f"m² → C_hi = {self.c_hi_kwp / 1e3:.1f} MWp (Anteil {ROOF_USABLE_FRACTION}, {KWP_PER_M2} kWp/m²; "
                    f"kein Solarkataster für die Gemeinde)")
        if self.implausible:
            text += f" | WARNUNG: {self.implausible} Dächer > {IMPLAUSIBLE_ROOF_M2:.0f} m²"
        return text


def fetch_infdb_roof_potential(ags: str, dsn: str = DEFAULT_DSN) -> RoofPotential:
    """Dachpotenzial der bewohnten Wohngebäude einer Gemeinde. Bricht ab, wenn die AGS nicht in der InfDB liegt."""
    import psycopg2

    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(CADASTRE_TABLES_SQL)
        imported = bool(cursor.fetchone()[0])
        if imported:
            cursor.execute(CADASTRE_IMPORTED_SQL, {"ags": ags})
            imported = bool(cursor.fetchone()[0])
        query = ROOF_SQL_WITH_CADASTRE if imported else ROOF_SQL
        cursor.execute(query, {"ags": ags})
        frame = pd.DataFrame(cursor.fetchall(), columns=["objectid", "roof_area_m2", "kwp"])
    if frame.empty:
        raise LookupError(f"AGS {ags} hat keine bewohnten Wohngebäude in der InfDB (basedata) — Gemeinde "
                          f"importieren und basedata-buildings laufen lassen.")
    area = frame["roof_area_m2"].astype(float)
    from_area = area * ROOF_USABLE_FRACTION * KWP_PER_M2
    if imported:
        potential = pd.to_numeric(frame["kwp"], errors="coerce").fillna(0.0)
    else:
        potential = from_area
    return RoofPotential(
        ags=ags,
        buildings=len(frame),
        source="solarkataster" if imported else "dachflaeche",
        without_suitable_roof=int((potential <= 0).sum()),
        roof_area_m2=float(area.sum()),
        c_hi_kwp=float(potential.sum()),
        c_hi_from_roof_area_kwp=float(from_area.sum()),
        implausible=int((area > IMPLAUSIBLE_ROOF_M2).sum()),
    )
