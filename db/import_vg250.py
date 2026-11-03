#!/usr/bin/env python3
"""Importiert VG250-Gemeindegrenzen (BKG) als Raumeinheiten.

Liest den Layer ``vg250_gem`` aus dem BKG-GeoPackage (Verwaltungsgebiete
1:250 000, Open Data dl-de/by-2-0), filtert ein Bundesland (Default NRW,
``SN_L='05'``) und die Landflächen (``GF=4``), reprojiziert auf EPSG:3035
(BUILDA-CRS) und schreibt je Gemeinde eine Zeile nach ``raumeinheit``
(``raum_code``=AGS, ``typ='gemeinde'``, ``name``=GEN, ``geom_wkt``, Provenienz
``quelle_id``=vg250). Grundlage für den Spatial-Join ([spatial_join.py]).

Bezug: https://gdz.bkg.bund.de → produkte/vg/vg250_ebenen_0101 (GeoPackage).

    python hochlauf_model/db/import_vg250.py --replace
    python hochlauf_model/db/import_vg250.py --gpkg data/.../DE_VG250.gpkg --bundesland 05
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import geopandas as gpd

DEFAULT_DB = Path(__file__).resolve().parents[1] / "hochlauf.sqlite"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ZIEL_CRS = "EPSG:3035"
GEM_LAYER = "vg250_gem"

DQ = dict(  # Provenienz (deckt sich mit seed_szenarien.sql datenquelle vg250)
    code="vg250", name="Verwaltungsgebiete 1:250 000 (VG250)",
    herausgeber="Bundesamt für Kartographie und Geodäsie (BKG)",
    url="https://gdz.bkg.bund.de", lizenz="dl-de/by-2-0", stand="2025-01-01",
    version="vg250_ebenen_0101",
    beschreibung="Gemeinde-/Kreisgrenzen DE (Ebene vg250_gem) — räumliche Zuordnung")


def _find_gpkg() -> Path:
    hits = list(DATA_DIR.rglob("DE_VG250.gpkg"))
    if not hits:
        raise SystemExit(f"Kein DE_VG250.gpkg unter {DATA_DIR} — VG250 erst herunterladen/entpacken.")
    return hits[0]


def _quelle_id(con) -> int:
    con.execute(
        "INSERT INTO datenquelle (code,name,herausgeber,url,lizenz,stand,version,beschreibung,abrufdatum) "
        "VALUES (:code,:name,:herausgeber,:url,:lizenz,:stand,:version,:beschreibung,date('now')) "
        "ON CONFLICT(code) DO NOTHING", DQ)
    return con.execute("SELECT id FROM datenquelle WHERE code='vg250'").fetchone()[0]


def _nrw_id(con, quelle_id) -> int | None:
    row = con.execute(
        "SELECT id FROM raumeinheit WHERE raum_code='Nordrhein-Westfalen'").fetchone()
    return row[0] if row else None


def run(db_path: Path, gpkg: Path, bundesland: str, replace: bool):
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    quelle_id = _quelle_id(con)
    parent_id = _nrw_id(con, quelle_id)

    gdf = gpd.read_file(gpkg, layer=GEM_LAYER)
    gdf = gdf[(gdf["SN_L"] == bundesland) & (gdf["GF"] == 4)].copy()
    if gdf.empty:
        raise SystemExit(f"Keine Gemeinden für SN_L={bundesland}/GF=4 gefunden.")
    gdf = gdf.to_crs(ZIEL_CRS)

    if replace:
        con.execute("DELETE FROM raumeinheit WHERE typ='gemeinde' AND quelle_id=?", (quelle_id,))

    n = 0
    for _, row in gdf.iterrows():
        ags, name, geom = row["AGS"], row["GEN"], row.geometry
        if geom is None or geom.is_empty:
            continue
        con.execute(
            "INSERT INTO raumeinheit (raum_code,typ,name,uebergeordnet_id,geom_wkt,quelle_id) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(raum_code) DO UPDATE SET name=excluded.name, geom_wkt=excluded.geom_wkt, "
            "uebergeordnet_id=excluded.uebergeordnet_id, quelle_id=excluded.quelle_id",
            (ags, "gemeinde", name, parent_id, geom.wkt, quelle_id))
        n += 1

    con.execute(
        "INSERT INTO import_log (quelle_id,ziel_tabelle,zeilen,skript_version,importiert_am) "
        "VALUES (?,?,?,?,datetime('now'))",
        (quelle_id, "raumeinheit", n, f"import_vg250 SN_L={bundesland} CRS→{ZIEL_CRS}"))
    con.commit()
    print(f"VG250: {n} Gemeinden (SN_L={bundesland}) → raumeinheit (typ='gemeinde', {ZIEL_CRS}).")
    con.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--gpkg", type=Path, default=None, help="Pfad zum DE_VG250.gpkg (Default: Suche in data/)")
    p.add_argument("--bundesland", default="05", help="SN_L-Schlüssel (05=NRW)")
    p.add_argument("--replace", action="store_true", help="bestehende VG250-Gemeinden ersetzen")
    args = p.parse_args(argv)
    gpkg = args.gpkg.resolve() if args.gpkg else _find_gpkg()
    run(args.db.resolve(), gpkg, args.bundesland, args.replace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
