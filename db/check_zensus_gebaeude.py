#!/usr/bin/env python3
"""Abgleich: bewohnte Wohngebäude der InfDB gegen Gebäude mit Wohnraum im Zensus 2022.

Das 100-m-Gitter des Zensus 2022 enthält nur Zellen mit mindestens 3 Gebäuden (Geheimhaltung). In ländlichen
Gemeinden mit Einzelhöfen fehlen dort deshalb viele Gebäude; die Summe über die 100-m-Zellen ist nur eine
Untergrenze. Belastbar ist der Vergleich im 1-km-Gitter über die Zellen, die ganz in der Gemeinde liegen.
Gebäude werden wie in InfDB (basedata-buildings) über ihren Schwerpunkt einer Zelle zugeordnet.

    python db/check_zensus_gebaeude.py 05374040 05374052
"""
from __future__ import annotations

import argparse

import psycopg2

DEFAULT_DSN = "postgresql://infdb_user:infdb@127.0.0.1:54338/infdb"

# Zellen (Größe s in m) ganz in der Gemeinde, Zensus-Gebäude und InfDB-Gebäude je Zelle
SQL = """
WITH gem AS (SELECT ST_Transform(geom, 3035) AS geom FROM opendata.bkg_vg5000_gem WHERE ags = %(ags)s),
infdb AS (
  SELECT floor(ST_X(ST_Transform(centroid, 3035)) / %(s)s) * %(s)s + %(s)s / 2 AS x,
         floor(ST_Y(ST_Transform(centroid, 3035)) / %(s)s) * %(s)s + %(s)s / 2 AS y, count(*) AS n
  FROM basedata.buildings
  WHERE gemeindeschluessel = %(ags)s AND building_type IS NOT NULL AND COALESCE(occupants, 0) > 0
  GROUP BY 1, 2),
zensus AS (
  SELECT z.{x} AS x, z.{y} AS y, z.insgesamt_gebaeude AS n,
         ST_Contains(gem.geom, ST_MakeEnvelope(z.{x} - %(s)s / 2, z.{y} - %(s)s / 2,
                                               z.{x} + %(s)s / 2, z.{y} + %(s)s / 2, 3035)) AS ganz_innen
  FROM opendata.{table} z, gem
  WHERE ST_Intersects(gem.geom, ST_MakeEnvelope(z.{x} - %(s)s / 2, z.{y} - %(s)s / 2,
                                                z.{x} + %(s)s / 2, z.{y} + %(s)s / 2, 3035)))
SELECT (SELECT sum(n) FROM infdb),
       (SELECT sum(n) FROM zensus),
       (SELECT sum(n) FROM zensus WHERE ganz_innen),
       (SELECT sum(i.n) FROM infdb i JOIN zensus z USING (x, y) WHERE z.ganz_innen)
"""
GRIDS = {
    "100 m": (100, "zensus_2022_100m_gebaeude_anzahl_wohnungen", "x_mp_100m", "y_mp_100m"),
    "1 km": (1000, "zensus_2022_1km_gebaeude_anzahl_wohnungen", "x_mp_1km", "y_mp_1km"),
}


def check(ags: str, dsn: str) -> None:
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        for name, (size, table, x, y) in GRIDS.items():
            cursor.execute(SQL.format(table=table, x=x, y=y), {"ags": ags, "s": size})
            infdb, zensus, zensus_inner, infdb_inner = (float(v or 0) for v in cursor.fetchone())
            if not zensus_inner:
                print(f"{ags} {name:>5}: keine Zensus-Zellen in der InfDB (Scope ohne diese Gemeinde?)")
                continue
            print(f"{ags} {name:>5}: InfDB {infdb:5.0f}, Zensus {zensus:5.0f} ({infdb / zensus - 1:+.1%}) | "
                  f"Zellen ganz innen: InfDB {infdb_inner:5.0f}, Zensus {zensus_inner:5.0f} "
                  f"({infdb_inner / zensus_inner - 1:+.1%})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ags", nargs="+")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    args = parser.parse_args()
    for ags in args.ags:
        check(ags, args.dsn)


if __name__ == "__main__":
    main()
