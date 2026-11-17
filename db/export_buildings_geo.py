#!/usr/bin/env python3
"""Bewohnte Wohngebäude einer Gemeinde mit Lage und Dach-PV-Potenzial für die Notebook-Karte.

Gleiche Gebäude und gleiche Regel wie C_hi (``pv_hochlauf/io/infdb_saturation.py``) und AP 2: Solarkataster NRW,
wo importiert (0 = kein geeignetes Dach), sonst LoD2-Dachfläche × 0,4 × 0,205 kWp/m².

    python db/export_buildings_geo.py 05374040 --out notebooks/data/reichshof_buildings_geo.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pv_hochlauf.io.infdb_saturation import (
    _BUILDINGS,
    _CADASTRE_JOIN,
    CADASTRE_IMPORTED_SQL,
    CADASTRE_TABLES_SQL,
    DEFAULT_DSN,
    KWP_PER_M2,
    ROOF_USABLE_FRACTION,
)

COLUMNS = """SELECT b.objectid, b.building_type,
       ST_X(ST_Transform(b.centroid, 4326)) AS lon, ST_Y(ST_Transform(b.centroid, 4326)) AS lat,
       COALESCE(r.roof_area_m2, 0) AS roof_m2, {kwp} AS kwp"""


def export(ags: str, dsn: str, out: str) -> None:
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(CADASTRE_TABLES_SQL)
        imported = bool(cursor.fetchone()[0])
        if imported:
            cursor.execute(CADASTRE_IMPORTED_SQL, {"ags": ags})
            imported = bool(cursor.fetchone()[0])
        if imported:
            sql = COLUMNS.format(kwp="COALESCE(k.kwp, 0)") + _BUILDINGS.format(cadastre_join=_CADASTRE_JOIN)
        else:
            sql = (COLUMNS.format(kwp=f"COALESCE(r.roof_area_m2, 0) * {ROOF_USABLE_FRACTION} * {KWP_PER_M2}")
                   + _BUILDINGS.format(cadastre_join=""))
        cursor.execute(sql + " ORDER BY b.objectid", {"ags": ags})
        frame = pd.DataFrame(cursor.fetchall(), columns=["objectid", "building_type", "lon", "lat", "roof_m2",
                                                         "kwp_potenzial"])
    frame = frame.astype({"lon": float, "lat": float, "roof_m2": float, "kwp_potenzial": float}).round(
        {"lon": 6, "lat": 6, "roof_m2": 0, "kwp_potenzial": 2})
    frame.to_csv(out, index=False)
    source = "Solarkataster NRW" if imported else "Dachfläche"
    print(f"{len(frame)} Wohngebäude, Σ {frame.kwp_potenzial.sum() / 1e3:.1f} MWp ({source}) → {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ags")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    export(args.ags, args.dsn, args.out)


if __name__ == "__main__":
    main()
