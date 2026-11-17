#!/usr/bin/env python3
"""Lädt das Solarkataster NRW (Photovoltaik auf Dachflächen, LANUK) je Gemeinde in die InfDB.

Quelle: Open.NRW, Datensatz "Solarkataster NRW: Potenzialdaten Dachflächen-Photovoltaik"
(https://ckan.open.nrw/dataset/6b1af6af-cd03-4206-a323-894eae1aaf08), Lizenz dl-de/zero-2.0.
Je Dachteilfläche: installierbare Leistung ``kw`` aus Laserscan-Oberflächenmodell, Verschattung, Dachaufbauten
und Modulbelegung. ``name`` ist die ALKIS-Gebäude-ID = ``objectid`` der InfDB (``basedata.buildings``).

Schreibt in das Schema ``opendata`` der InfDB, mit denselben Tabellen und Spalten wie die InfDB-Importquelle
``solarkataster-nrw`` (Fork-Branch ``feature/solarkataster-nrw``, PR an tum-ens/InfDB). Übergangslösung, bis die
Quelle upstream verfügbar ist; danach diesen Importer löschen.
  solarkataster_nrw_pv_dach  eine Zeile je Dachteilfläche (Attribute + Geometrie, EPSG:25832)
  solarkataster_nrw_import   eine Zeile je importierter Gemeinde (Datei, Stand, Zeitpunkt, Flächen, Σ kW)

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
SURFACES, IMPORTS = "solarkataster_nrw_pv_dach", "solarkataster_nrw_import"
SRID = 25832

# Spalte in der InfDB ← (Feld im Shape, Typ, Kommentar) — identisch mit InfDB solarkataster_nrw.py
COLUMNS = {
    "objectid": ("name", "text", "ALKIS building ID (= objectid of the LoD2 building)"),
    "gemeindeschluessel": ("gem_kn", "text", "Municipality key (AGS)"),
    "lanuk_id": ("LANUK_ID", "text", "ID of the roof surface in the Solarkataster NRW"),
    "geb_id": ("geb_id", "text", "Building ID in the Solarkataster NRW"),
    "mod_id": ("mod_id", "text", "Module layout ID in the Solarkataster NRW"),
    "dachtyp": ("dachtyp", "text", "Roof type (flach = flat, geneigt = pitched)"),
    "richtung": ("richtung", "integer", "Azimuth in degree (180 = south, -1 = flat roof)"),
    "neigung": ("neigung", "integer", "Tilt in degree"),
    "himmel_kat": ("himmel_kat", "text", "Orientation category"),
    "modarea": ("modarea", "double precision", "Roof area suited for modules in m2"),
    "anzahl": ("anzahl", "integer", "Number of modules"),
    "modanetto": ("modanetto", "double precision", "Net module area in m2"),
    "kw": ("kw", "double precision", "Installable PV capacity in kWp"),
    "kwh_kwp": ("kwh_kwp", "double precision", "Specific annual yield in kWh/kWp"),
    "str": ("str", "double precision", "Annual electricity yield in kWh"),
    "yr_median": ("yr_median", "double precision", "Median annual irradiation in kWh/m2"),
    "jahr": ("jahr", "integer", "Year of the laser scan flight"),
}


def create_tables(cursor) -> None:
    cols = ",\n  ".join(f"{name} {sql_type}" for name, (_, sql_type, _) in COLUMNS.items())
    comments = "\n".join(f"COMMENT ON COLUMN {SCHEMA}.{SURFACES}.{name} IS '{comment}';"
                         for name, (_, _, comment) in COLUMNS.items())
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{SURFACES} (
          {cols},
          geom geometry(MultiPolygon, {SRID})
        );
        CREATE INDEX IF NOT EXISTS {SURFACES}_objectid_idx ON {SCHEMA}.{SURFACES} (objectid);
        CREATE INDEX IF NOT EXISTS {SURFACES}_gemeindeschluessel_idx ON {SCHEMA}.{SURFACES} (gemeindeschluessel);
        CREATE INDEX IF NOT EXISTS {SURFACES}_geom_idx ON {SCHEMA}.{SURFACES} USING GIST (geom);
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{IMPORTS} (
          ags text PRIMARY KEY,
          file_name text NOT NULL,
          file_timestamp timestamp,
          imported_at timestamptz NOT NULL,
          roof_surfaces integer NOT NULL,
          kw_total double precision NOT NULL
        );
        COMMENT ON TABLE {SCHEMA}.{SURFACES} IS
          'Solarkataster NRW (LANUK): roof surfaces suited for PV, dl-de/zero-2.0';
        COMMENT ON TABLE {SCHEMA}.{IMPORTS} IS
          'Imported municipalities; a building there without roof surface has no roof suited for PV';
        {comments}
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
    missing = [src for src, _, _ in COLUMNS.values() if src not in position]
    if missing:
        raise SystemExit(f"Felder fehlen im Shape: {missing}")
    rows = []
    for k, wkb in enumerate(geometry):
        geom = shapely.from_wkb(wkb)
        if geom.geom_type == "Polygon":
            geom = shapely.MultiPolygon([geom])
        values = tuple(_plain(fields[position[src]][k]) for src, _, _ in COLUMNS.values())
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
    other = {r[1] for r in rows} - {ags}
    if other:
        print(f"  Hinweis: Flächen mit anderem Gemeindeschlüssel in der Datei: {sorted(other)}")
    names = ", ".join(COLUMNS)
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        create_tables(cursor)
        keys = sorted({r[1] for r in rows} | {ags})
        cursor.execute(f"DELETE FROM {SCHEMA}.{SURFACES} WHERE gemeindeschluessel = ANY(%s)", (keys,))
        execute_values(cursor,
                       f"INSERT INTO {SCHEMA}.{SURFACES} ({names}, geom) VALUES %s",
                       rows,
                       template="(" + ", ".join(["%s"] * len(COLUMNS)) + f", ST_GeomFromWKB(decode(%s, 'hex'), {SRID}))",
                       page_size=2000)
        kw_sum = sum(r[list(COLUMNS).index("kw")] or 0 for r in rows)
        cursor.execute(f"""
            INSERT INTO {SCHEMA}.{IMPORTS} (ags, file_name, file_timestamp, imported_at, roof_surfaces, kw_total)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (ags) DO UPDATE SET file_name = EXCLUDED.file_name,
              file_timestamp = EXCLUDED.file_timestamp, imported_at = EXCLUDED.imported_at,
              roof_surfaces = EXCLUDED.roof_surfaces, kw_total = EXCLUDED.kw_total""",
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
