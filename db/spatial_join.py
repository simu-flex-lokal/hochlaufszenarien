#!/usr/bin/env python3
"""Spatial-Join — ordnet Gebäude einer Raumeinheit zu (setzt ``gebaeude.raum_id``).

Point-in-Polygon der Gebäude-Centroids (``gebaeude.geom_wkt``, EPSG:3035) in die
Raumeinheit-Polygone (Default ``typ='gemeinde'``, aus [import_vg250.py]). Nutzt
einen STRtree (shapely) für die vektorisierte Zuordnung. Macht Komponente A
([potential.py]) und B ([allocation.py]) **raum-scharf** (je Gemeinde statt
eines Aggregats).

    python hochlauf_model/db/spatial_join.py
    python hochlauf_model/db/spatial_join.py --typ gemeinde
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from shapely import STRtree, from_wkt

DEFAULT_DB = Path(__file__).resolve().parents[1] / "hochlauf.sqlite"


def run(db_path: Path, typ: str, only_null: bool):
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    raum = con.execute(
        "SELECT id, geom_wkt FROM raumeinheit WHERE typ=? AND geom_wkt IS NOT NULL", (typ,)
    ).fetchall()
    if not raum:
        raise SystemExit(f"Keine Raumeinheit-Polygone (typ='{typ}') — erst import_vg250.py.")
    raum_ids = [r[0] for r in raum]
    polys = [from_wkt(r[1]) for r in raum]
    tree = STRtree(polys)

    where = "geom_wkt IS NOT NULL" + (" AND raum_id IS NULL" if only_null else "")
    geb = con.execute(f"SELECT id, geom_wkt FROM gebaeude WHERE {where}").fetchall()
    if not geb:
        raise SystemExit("Keine Gebäude mit Geometrie zu verorten.")
    geb_ids = [g[0] for g in geb]
    pts = [from_wkt(g[1]) for g in geb]

    # Vektorisiert: (input_idx, tree_idx)-Paare, Punkt schneidet Polygon (inkl. Rand).
    pairs = tree.query(pts, predicate="intersects")
    zuordnung: dict[int, int] = {}
    for in_i, tree_j in zip(pairs[0].tolist(), pairs[1].tolist()):
        zuordnung.setdefault(in_i, raum_ids[tree_j])  # erster Treffer (Randfälle)

    updates = [(zuordnung[i], geb_ids[i]) for i in zuordnung]
    con.executemany("UPDATE gebaeude SET raum_id=? WHERE id=?", updates)
    con.commit()

    matched = len(zuordnung)
    total = len(geb_ids)
    print(f"Spatial-Join (typ='{typ}'): {matched:,}/{total:,} Gebäude verortet "
          f"({total - matched:,} ohne Treffer).")
    verteilung = con.execute(
        "SELECT r.name, count(*) FROM gebaeude g JOIN raumeinheit r ON r.id=g.raum_id "
        "WHERE r.typ=? GROUP BY r.name ORDER BY count(*) DESC LIMIT 8", (typ,)).fetchall()
    print("Top-Gemeinden:", ", ".join(f"{n}={c}" for n, c in verteilung))
    con.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--typ", default="gemeinde", help="Raumeinheit-Typ mit Polygonen")
    p.add_argument("--only-null", action="store_true", help="nur Gebäude ohne raum_id zuordnen")
    args = p.parse_args(argv)
    run(args.db.resolve(), args.typ, args.only_null)
    return 0


if __name__ == "__main__":
    sys.exit(main())
