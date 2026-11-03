#!/usr/bin/env python3
"""Baut ``hochlauf.sqlite`` reproduzierbar aus ``schema.sql`` + ``seed_*.sql``.

Nur Standardbibliothek. Die DB ist ein wegwerfbares Build-Artefakt (gitignored);
die Wahrheit liegt in den versionierten SQL-Dateien. Rohdaten-Import
(BUILDA/MaStR/KBA/…) erfolgt separat und protokolliert in ``import_log``.

Beispiel:
    python hochlauf_model/db/build_db.py            # baut hochlauf_model/hochlauf.sqlite
    python hochlauf_model/db/build_db.py --db /tmp/h.sqlite
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent           # hochlauf_model/db
DEFAULT_DB = DB_DIR.parent / "hochlauf.sqlite"       # hochlauf_model/hochlauf.sqlite
DB_SUFFIXE = {".sqlite", ".sqlite3", ".db"}


def _apply_sql(con: sqlite3.Connection, path: Path) -> None:
    """Führt eine SQL-Datei als Skript aus."""
    con.executescript(path.read_text(encoding="utf-8"))


def _verify(con: sqlite3.Connection) -> None:
    """Prüft Fremdschlüssel und Integrität; bricht bei Verletzungen ab."""
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        raise SystemExit(f"FEHLER: Fremdschlüssel-Verletzungen: {fk}")
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    if integ != "ok":
        raise SystemExit(f"FEHLER: integrity_check: {integ}")


def _summary(con: sqlite3.Connection) -> None:
    """Gibt Zeilenzahlen je Tabelle aus."""
    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    print("Tabellen:")
    for t in tables:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608 (feste Namen)
        marker = "" if n else "  (leer)"
        print(f"  {t:20s} {n:>7d}{marker}")


def build(db_path: Path, db_dir: Path = DB_DIR, force: bool = False) -> Path:
    """Baut die DB frisch aus schema.sql + seed_*.sql."""
    schema = db_dir / "schema.sql"
    if not schema.exists():
        raise FileNotFoundError(f"schema.sql fehlt: {schema}")
    seeds = sorted(db_dir.glob("seed_*.sql"))

    if db_path.exists():
        if db_path.suffix not in DB_SUFFIXE and not force:
            raise SystemExit(
                f"Abbruch: {db_path} sieht nicht wie eine DB-Datei aus "
                f"(erwartet {sorted(DB_SUFFIXE)}); mit --force überschreiben."
            )
        db_path.unlink()
        print(f"Bestehende DB überschrieben: {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        print(f"Schema:  {schema.name}")
        _apply_sql(con, schema)
        for s in seeds:
            print(f"Seed:    {s.name}")
            _apply_sql(con, s)
        con.commit()
        _verify(con)
        print(f"\nDB gebaut: {db_path}")
        _summary(con)
    finally:
        con.close()
    return db_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"Zielpfad der DB (Default: {DEFAULT_DB})")
    p.add_argument("--db-dir", type=Path, default=DB_DIR, help="Verzeichnis mit schema.sql/seed_*.sql")
    p.add_argument("--force", action="store_true", help="Zielpfad auch ohne DB-Endung überschreiben")
    args = p.parse_args(argv)
    build(args.db.resolve(), args.db_dir.resolve(), force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
