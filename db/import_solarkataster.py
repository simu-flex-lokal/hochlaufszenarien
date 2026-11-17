#!/usr/bin/env python3
"""Lädt das Solarkataster NRW (Photovoltaik auf Dachflächen, LANUK) je Gemeinde in die InfDB.

Quelle: Open.NRW, Datensatz "Solarkataster NRW: Potenzialdaten Dachflächen-Photovoltaik"
(https://ckan.open.nrw/dataset/6b1af6af-cd03-4206-a323-894eae1aaf08), Lizenz dl-de/zero-2.0.
Je Dachteilfläche: installierbare Leistung ``kw`` aus Laserscan-Oberflächenmodell, Verschattung, Dachaufbauten
und Modulbelegung. ``name`` ist die ALKIS-Gebäude-ID = ``objectid`` der InfDB (``basedata.buildings``).

Schreibt in das Schema ``opendata`` der InfDB:
  solarkataster_pv_dach    eine Zeile je Dachteilfläche (Attribute + Geometrie, EPSG:25832)
  solarkataster_pv_import  eine Zeile je importierter Gemeinde (Datei, Stand, Zeitpunkt, Flächen, Σ kW)

Die Import-Tabelle zeigt, für welche Gemeinden das Kataster vorliegt: Ein Wohngebäude einer solchen Gemeinde
ohne Dachteilfläche hat laut Kataster kein geeignetes Dach (zu klein oder stark verschattet). AP 2
(ObjectTypeGenerator) und AP 3.1 (``pv_hochlauf/io/infdb_saturation.py``) lesen das Potenzial von hier.

Beispiel:
    python db/import_solarkataster.py 05374040            # Reichshof
    python db/import_solarkataster.py 05374040 05374052   # mehrere Gemeinden
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

BASE_URL = "https://www.opengeodata.nrw.de/produkte/umwelt_klima/energie/solarkataster/photovoltaik"
DEFAULT_DSN = "postgresql://infdb_user:infdb@127.0.0.1:54328/infdb"
SCHEMA = "opendata"
SURFACES, IMPORTS = "solarkataster_pv_dach", "solarkataster_pv_import"
SRID = 25832

# Spalte in der InfDB ← Feld im Shape (Shape-Feldnamen sind auf 10 Zeichen gekürzt)
COLUMNS = {
    "lanuk_id": ("LANUK_ID", "text"),
    "objectid": ("name", "text"),          # ALKIS-Gebäude-ID = InfDB basedata.buildings.objectid
    "geb_id": ("geb_id", "text"),
    "mod_id": ("mod_id", "text"),
    "gemeindeschluessel": ("gem_kn", "text"),
    "dachtyp": ("dachtyp", "text"),
    "himmel_kat": ("himmel_kat", "text"),
    "richtung_grad": ("richtung", "integer"),   # -1 = Flachdach, 180 = Süd
    "neigung_grad": ("neigung", "integer"),
    "modarea_m2": ("modarea", "double precision"),
    "anzahl_module": ("anzahl", "integer"),
    "modul_netto_m2": ("modanetto", "double precision"),
    "kw": ("kw", "double precision"),            # installierbare Leistung [kWp]
    "kwh_kwp": ("kwh_kwp", "double precision"),  # spezifischer Ertrag [kWh/kWp·a]
    "ertrag_kwh": ("str", "double precision"),   # Stromertrag [kWh/a]
    "jahr": ("jahr", "integer"),                 # Befliegungsjahr der Laserscan-Daten
}


def create_tables(cursor) -> None:
    cols = ",\n  ".join(f"{name} {sql_type}" for name, (_, sql_type) in COLUMNS.items())
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{SURFACES} (
          {cols},
          geom geometry(MultiPolygon, {SRID})
        );
        CREATE INDEX IF NOT EXISTS {SURFACES}_objectid_idx ON {SCHEMA}.{SURFACES} (objectid);
        CREATE INDEX IF NOT EXISTS {SURFACES}_ags_idx ON {SCHEMA}.{SURFACES} (gemeindeschluessel);
        CREATE INDEX IF NOT EXISTS {SURFACES}_geom_idx ON {SCHEMA}.{SURFACES} USING GIST (geom);
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{IMPORTS} (
          gemeindeschluessel text PRIMARY KEY,
          datei text NOT NULL,
          datei_stand timestamptz,
          importiert_am timestamptz NOT NULL,
          flaechen integer NOT NULL,
          kw_summe double precision NOT NULL
        );
        COMMENT ON TABLE {SCHEMA}.{SURFACES} IS
          'Solarkataster NRW (LANUK), PV-geeignete Dachteilflächen; dl-de/zero-2.0; objectid = ALKIS-ID';
        COMMENT ON TABLE {SCHEMA}.{IMPORTS} IS
          'Gemeinden, für die das Solarkataster NRW importiert ist (Wohngebäude ohne Fläche: kein geeignetes Dach)';
    """)


def shape_file_for(ags: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}/index.json", timeout=60) as response:
        index = json.load(response)
    shapes = next(d for d in index["datasets"] if d["name"].endswith("_Shape"))
    matches = [f for f in shapes["files"] if f"_{ags}_" in f["name"]]
    if not matches:
        raise SystemExit(f"Kein Solarkataster-Shape für AGS {ags} (nur NRW-Gemeinden, 05…).")
    return matches[0]


def read_surfaces(zip_path: Path) -> list[tuple]:
    import shapely
    from pyogrio.raw import read

    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(directory)
        shp = next(Path(directory).rglob("*.shp"))
        meta, _, geometry, fields = read(shp)
    crs = meta.get("crs") or ""
    if str(SRID) not in crs:
        raise SystemExit(f"Unerwartetes Koordinatensystem {crs!r} (erwartet EPSG:{SRID}).")
    position = {name: i for i, name in enumerate(meta["fields"])}
    missing = [src for src, _ in COLUMNS.values() if src not in position]
    if missing:
        raise SystemExit(f"Felder fehlen im Shape: {missing}")
    rows = []
    for k, wkb in enumerate(geometry):
        geom = shapely.from_wkb(wkb)
        if geom.geom_type == "Polygon":
            geom = shapely.MultiPolygon([geom])
        values = tuple(_plain(fields[position[src]][k]) for src, _ in COLUMNS.values())
        rows.append(values + (shapely.to_wkb(geom, hex=True, include_srid=False),))
    return rows


def _plain(value):
    """numpy-Skalare → Python-Typen (psycopg2)."""
    return value.item() if hasattr(value, "item") else value


def import_municipality(ags: str, dsn: str) -> None:
    entry = shape_file_for(ags)
    print(f"{ags}: lade {entry['name']} ({int(entry['size']) / 1e6:.0f} MB) …")
    with tempfile.TemporaryDirectory() as directory:
        zip_path = Path(directory) / entry["name"]
        urllib.request.urlretrieve(f"{BASE_URL}/{entry['name']}", zip_path)
        rows = read_surfaces(zip_path)
    other = {r[4] for r in rows} - {ags}
    if other:
        print(f"  Hinweis: Flächen mit anderem Gemeindeschlüssel in der Datei: {sorted(other)}")
    names = ", ".join(COLUMNS)
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        create_tables(cursor)
        cursor.execute(f"DELETE FROM {SCHEMA}.{SURFACES} WHERE gemeindeschluessel = %s", (ags,))
        execute_values(cursor,
                       f"INSERT INTO {SCHEMA}.{SURFACES} ({names}, geom) VALUES %s",
                       rows,
                       template="(" + ", ".join(["%s"] * len(COLUMNS)) + f", ST_GeomFromWKB(decode(%s, 'hex'), {SRID}))",
                       page_size=2000)
        kw_sum = sum(r[list(COLUMNS).index("kw")] or 0 for r in rows)
        cursor.execute(f"""
            INSERT INTO {SCHEMA}.{IMPORTS} VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (gemeindeschluessel) DO UPDATE SET datei = EXCLUDED.datei,
              datei_stand = EXCLUDED.datei_stand, importiert_am = EXCLUDED.importiert_am,
              flaechen = EXCLUDED.flaechen, kw_summe = EXCLUDED.kw_summe""",
                       (ags, entry["name"], entry.get("timestamp"), dt.datetime.now(dt.timezone.utc),
                        len(rows), kw_sum))
    print(f"  {len(rows)} Dachteilflächen, Σ {kw_sum / 1e3:.1f} MWp → {SCHEMA}.{SURFACES}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ags", nargs="+", help="Amtlicher Gemeindeschlüssel (8-stellig, NRW)")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    args = parser.parse_args()
    for ags in args.ags:
        if not (len(ags) == 8 and ags.isdigit() and ags.startswith("05")):
            sys.exit(f"Ungültige NRW-AGS: {ags}")
        import_municipality(ags, args.dsn)


if __name__ == "__main__":
    main()
