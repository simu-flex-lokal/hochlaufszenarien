#!/usr/bin/env python3
"""Importiert ETHOS.BUILDA (NRW = DEA.csv) in die Tabelle ``gebaeude``.

Filtert auf Einfamilienhäuser (``size_class == 'SFH'``) und optional auf eine
Bounding-Box (EPSG:3035). Streamt die Datei (DEA.csv ~1,6 GB) und schreibt die
attributweise BUILDA-Provenienz (value/source/lineage) mit. Protokolliert den
Lauf in ``import_log``. Nur Standardbibliothek.

BUILDA-CSV-Format (Kopf): id, position, construction_year, size_class,
refurbishment_state, tabula_type — die vier Attribute sind JSON-Objekte
``{"value","source","lineage"}``. Quelle: Zenodo 10.5281/zenodo.12069755 (ODbL).

Beispiel:
    python hochlauf_model/db/import_builda.py --csv data/DEA.csv
    python hochlauf_model/db/import_builda.py --csv data/DEA.csv --replace
    python hochlauf_model/db/import_builda.py --csv sample.csv --limit 1000
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterator

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_DIR.parent / "hochlauf.sqlite"
QUELLE_CODE = "builda"
VERSION = "import_builda/0.1"
EFH_DEFAULT = ("SFH",)  # BUILDA size_class: SFH=EFH, MFH, TH(Reihenhaus), AB
# CSV-Felder mit großen JSON-Strings — Limit großzügig setzen
csv.field_size_limit(1 << 20)

INSERT_SQL = """
INSERT INTO gebaeude
  (externe_id, raum_id, geom_wkt, gebaeudetyp, baujahr, sanierung, tabula_typ,
   heizart, gasnetz_anschluss,
   baujahr_source, baujahr_lineage, sanierung_source, sanierung_lineage,
   tabula_source, tabula_lineage, quelle_id)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""


def _attr(cell: str) -> tuple[object, object, object]:
    """Zerlegt ein BUILDA-Attribut-JSON in (value, source, lineage)."""
    try:
        d = json.loads(cell)
        return d.get("value"), d.get("source"), d.get("lineage")
    except (json.JSONDecodeError, TypeError):
        return None, None, None


def _point_xy(wkt: str) -> tuple[float, float] | None:
    """Extrahiert (x, y) aus 'POINT(x y)'."""
    try:
        inner = wkt[wkt.index("(") + 1 : wkt.rindex(")")]
        x, y = inner.split()
        return float(x), float(y)
    except (ValueError, AttributeError):
        return None


def _open(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "rt", encoding="utf-8", newline="")


def _rows(
    csv_path: Path,
    efh_classes: set[str],
    bbox: tuple[float, float, float, float] | None,
    limit: int | None,
    quelle_id: int,
    stats: dict[str, int],
) -> Iterator[tuple]:
    """Liest, filtert und mappt BUILDA-Zeilen auf gebaeude-Tupel."""
    with _open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or header[:6] != [
            "id", "position", "construction_year", "size_class",
            "refurbishment_state", "tabula_type",
        ]:
            raise SystemExit(f"Unerwarteter CSV-Kopf: {header}")
        for row in reader:
            stats["gelesen"] += 1
            if len(row) < 6:
                stats["defekt"] += 1
                continue
            size_val, _, _ = _attr(row[3])
            if size_val not in efh_classes:
                stats["kein_efh"] += 1
                continue
            if bbox is not None:
                xy = _point_xy(row[1])
                if xy is None or not (bbox[0] <= xy[0] <= bbox[2] and bbox[1] <= xy[1] <= bbox[3]):
                    stats["ausserhalb_bbox"] += 1
                    continue
            by_v, by_s, by_l = _attr(row[2])
            rs_v, rs_s, rs_l = _attr(row[4])
            tb_v, tb_s, tb_l = _attr(row[5])
            baujahr = by_v if isinstance(by_v, int) else None
            yield (
                row[0], None, row[1], size_val, baujahr, rs_v, tb_v,
                None, None,
                by_s, by_l, rs_s, rs_l, tb_s, tb_l, quelle_id,
            )
            stats["importiert"] += 1
            if limit is not None and stats["importiert"] >= limit:
                return


def import_builda(
    csv_path: Path,
    db_path: Path = DEFAULT_DB,
    efh_classes: tuple[str, ...] = EFH_DEFAULT,
    bbox: tuple[float, float, float, float] | None = None,
    limit: int | None = None,
    replace: bool = False,
    batch: int = 50_000,
) -> dict[str, int]:
    if not csv_path.exists():
        raise SystemExit(f"CSV nicht gefunden: {csv_path}")
    if not db_path.exists():
        raise SystemExit(f"DB nicht gefunden: {db_path} — zuerst build_db.py ausführen.")

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    row = con.execute("SELECT id FROM datenquelle WHERE code = ?", (QUELLE_CODE,)).fetchone()
    if row is None:
        raise SystemExit(f"Datenquelle '{QUELLE_CODE}' fehlt — Seed nicht angewandt?")
    quelle_id = row[0]

    vorhanden = con.execute(
        "SELECT count(*) FROM gebaeude WHERE quelle_id = ?", (quelle_id,)
    ).fetchone()[0]
    if vorhanden and not replace:
        raise SystemExit(
            f"Abbruch: {vorhanden} BUILDA-Gebäude bereits vorhanden. "
            f"Mit --replace ersetzen."
        )
    if vorhanden and replace:
        con.execute("DELETE FROM gebaeude WHERE quelle_id = ?", (quelle_id,))
        print(f"{vorhanden} bestehende BUILDA-Gebäude gelöscht (--replace).")

    stats = dict.fromkeys(
        ["gelesen", "importiert", "kein_efh", "ausserhalb_bbox", "defekt"], 0
    )
    src = _rows(csv_path, set(efh_classes), bbox, limit, quelle_id, stats)
    buf: list[tuple] = []
    for rec in src:
        buf.append(rec)
        if len(buf) >= batch:
            con.executemany(INSERT_SQL, buf)
            con.commit()
            buf.clear()
            print(f"  … {stats['importiert']:,} EFH importiert", flush=True)
    if buf:
        con.executemany(INSERT_SQL, buf)

    con.execute(
        "INSERT INTO import_log (quelle_id, ziel_tabelle, zeilen, skript_version, importiert_am) "
        "VALUES (?,?,?,?,?)",
        (quelle_id, "gebaeude", stats["importiert"], VERSION,
         _dt.datetime.now().isoformat(timespec="seconds")),
    )
    con.commit()
    con.close()

    print("\nImport abgeschlossen:")
    for k, v in stats.items():
        print(f"  {k:16s} {v:>10,}")
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--csv", type=Path, required=True, help="Pfad zu DEA.csv (NRW) oder .csv.gz")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"DB-Pfad (Default: {DEFAULT_DB})")
    p.add_argument("--efh-classes", nargs="+", default=list(EFH_DEFAULT),
                   help="size_class-Codes als EFH (Default: SFH; TH für Reihenhäuser ergänzbar)")
    p.add_argument("--bbox", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"),
                   help="Bounding-Box in EPSG:3035 (optional, Studienregion)")
    p.add_argument("--limit", type=int, help="max. Anzahl importierter EFH (Test)")
    p.add_argument("--replace", action="store_true", help="bestehende BUILDA-Gebäude ersetzen")
    p.add_argument("--batch", type=int, default=50_000, help="Insert-Batchgröße")
    args = p.parse_args(argv)
    import_builda(
        args.csv.resolve(), args.db.resolve(), tuple(args.efh_classes),
        tuple(args.bbox) if args.bbox else None, args.limit, args.replace, args.batch,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
