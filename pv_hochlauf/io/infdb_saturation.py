"""io/infdb_saturation.py — Dachpotenzial C_hi aus der InfDB.

Gleiche Datenbasis wie AP 2 (ObjectTypeGenerator) und die Netzsimulation (pylovo in der InfDB):
Wohngebäude aus ``basedata.buildings`` (``building_type`` gesetzt) mit ihren LoD2-Dachflächen aus
``basedata.building_surface_area``. Gleiche Formel wie AP 2 (Dach-Deckel je Gebäude):

    C_hi [kWp] = Σ_Wohngebäude Dachfläche_m2 × nutzbarer Anteil × kWp/m²

Die beiden Faktoren müssen mit ``SizingSettings`` in AP 2 übereinstimmen, sonst passen die Summe der
Gebäude-Dachpotenziale (AP 2) und die Sättigung der Gemeinde (AP 3.1) nicht zusammen.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

DEFAULT_DSN = "postgresql://infdb_user:infdb@127.0.0.1:54328/infdb"
ROOF_USABLE_FRACTION = 0.4  # = objecttypegenerator SizingSettings.pv_roof_usable_fraction
KWP_PER_M2 = 0.205          # = objecttypegenerator SizingSettings.pv_kwp_per_m2
IMPLAUSIBLE_ROOF_M2 = 5_000.0  # nur Hinweis: so große Dächer bei Wohngebäuden deuten auf fehlerhafte Geometrie

ROOF_SQL = """
SELECT b.objectid, b.building_type, COALESCE(r.roof_area_m2, 0) AS roof_area_m2
FROM basedata.buildings b
LEFT JOIN (SELECT building_objectid, SUM(area) AS roof_area_m2
           FROM basedata.building_surface_area
           WHERE classname = 'RoofSurface'
           GROUP BY building_objectid) r ON r.building_objectid = b.objectid
WHERE b.gemeindeschluessel = %(ags)s
  AND b.building_type IS NOT NULL
"""


@dataclass(frozen=True)
class RoofPotential:
    ags: str
    buildings: int
    without_roof: int
    roof_area_m2: float
    c_hi_kwp: float
    implausible: int  # Wohngebäude mit Dach > IMPLAUSIBLE_ROOF_M2

    def summary(self) -> str:
        text = (f"InfDB {self.ags}: {self.buildings} Wohngebäude, Dachfläche {self.roof_area_m2 / 1e3:.0f} Tsd. m² "
                f"→ C_hi = {self.c_hi_kwp / 1e3:.1f} MWp (Anteil {ROOF_USABLE_FRACTION}, {KWP_PER_M2} kWp/m²)")
        if self.without_roof:
            text += f" | {self.without_roof} ohne Dachfläche"
        if self.implausible:
            text += f" | WARNUNG: {self.implausible} Dächer > {IMPLAUSIBLE_ROOF_M2:.0f} m²"
        return text


def fetch_infdb_roof_potential(ags: str, dsn: str = DEFAULT_DSN) -> RoofPotential:
    """Dachpotenzial der Wohngebäude einer Gemeinde. Bricht ab, wenn die AGS nicht in der InfDB liegt."""
    import psycopg2

    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(ROOF_SQL, {"ags": ags})
        frame = pd.DataFrame(cursor.fetchall(), columns=["objectid", "building_type", "roof_area_m2"])
    if frame.empty:
        raise LookupError(f"AGS {ags} hat keine Wohngebäude in der InfDB (basedata) — Gemeinde importieren "
                          f"und basedata-buildings laufen lassen.")
    area = frame["roof_area_m2"].astype(float)
    return RoofPotential(
        ags=ags,
        buildings=len(frame),
        without_roof=int((area <= 0).sum()),
        roof_area_m2=float(area.sum()),
        c_hi_kwp=float(area.sum()) * ROOF_USABLE_FRACTION * KWP_PER_M2,
        implausible=int((area > IMPLAUSIBLE_ROOF_M2).sum()),
    )
