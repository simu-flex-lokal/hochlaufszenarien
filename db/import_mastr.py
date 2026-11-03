#!/usr/bin/env python3
"""Importiert MaStR (PV + Batteriespeicher) aus PostgreSQL in ``historie`` + ``bestand_ist``.

Quelle: Open-Energy-Data-Server (mastr-2025), read-only. Aggregiert die
Einzelanlagen zu Jahres-Zeitreihen (Zubau + kumulierter Bestand) je Raumeinheit
und einem Basisjahr-Snapshot — Grundlage für den Diffusions-Fit (Komponente C)
und den Ist-Bestand P(t0). Provenienz über ``quelle_id`` (mastr) + ``import_log``.

Benötigt ``psycopg2`` (PostgreSQL-Treiber). Nutzt die SQLite-DB aus build_db.py.

Beispiele:
    python hochlauf_model/db/import_mastr.py                       # NRW gesamt
    python hochlauf_model/db/import_mastr.py --level plz --replace
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sqlite3
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:  # pragma: no cover
    sys.exit("psycopg2 fehlt — installieren (z.B. apt: python3-psycopg2).")

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_DIR.parent / "hochlauf.sqlite"
DEFAULT_DSN = "postgresql://readonly:readonly@timescale.nowum.fh-aachen.de:5432/opendata"
MASTR_SCHEMA = "mastr-2025"
VERSION = "import_mastr/0.1"

# Raum-Ebene → (raum_typ, Spalte in MaStR).  'nrw' = eine Raumeinheit.
LEVEL = {
    "nrw": ("bundesland", None),
    "plz": ("plz", "Postleitzahl"),
    "gemeinde": ("gemeinde", "Gemeindeschluessel"),
}


def _pv_query(level_col: str | None) -> str:
    raum = f'e."{level_col}"::text' if level_col else "%(raum)s"
    where_raum = f'AND e."{level_col}" IS NOT NULL' if level_col else ""
    return f"""
        SELECT {raum} AS raum_code,
               EXTRACT(YEAR FROM e."Inbetriebnahmedatum")::int AS jahr,
               count(*) AS anzahl,
               sum(e."Bruttoleistung") AS kw,
               NULL::double precision AS kwh
        FROM "{MASTR_SCHEMA}".solar_extended e
        WHERE e."Bundesland" = %(bl)s
          AND e."EinheitBetriebsstatus" = 'In Betrieb'
          AND e."Nutzungsbereich" = %(nutzung)s
          AND e."Bruttoleistung" <= %(maxkw)s
          AND e."Inbetriebnahmedatum" BETWEEN %(dmin)s AND %(dmax)s
          {where_raum}
        GROUP BY 1, 2
    """


def _storage_query(level_col: str | None) -> str:
    raum = f'e."{level_col}"::text' if level_col else "%(raum)s"
    where_raum = f'AND e."{level_col}" IS NOT NULL' if level_col else ""
    return f"""
        SELECT {raum} AS raum_code,
               EXTRACT(YEAR FROM e."Inbetriebnahmedatum")::int AS jahr,
               count(*) AS anzahl,
               sum(e."Nettonennleistung") AS kw,
               sum(u.kwh) AS kwh
        FROM "{MASTR_SCHEMA}".storage_extended e
        LEFT JOIN (
            SELECT "VerknuepfteEinheit" AS v, sum("NutzbareSpeicherkapazitaet") AS kwh
            FROM "{MASTR_SCHEMA}".storage_units GROUP BY 1
        ) u ON u.v = e."EinheitMastrNummer"
        WHERE e."Bundesland" = %(bl)s
          AND e."EinheitBetriebsstatus" = 'In Betrieb'
          AND e."Nettonennleistung" <= %(maxkw)s
          AND e."Inbetriebnahmedatum" BETWEEN %(dmin)s AND %(dmax)s
          {where_raum}
        GROUP BY 1, 2
    """


TECHS = {
    "pv": (_pv_query, "Bruttoleistung"),
    "batteriespeicher": (_storage_query, "Nettonennleistung"),
}


def _fetch(dsn: str, sql: str, params: dict) -> list[tuple]:
    con = psycopg2.connect(dsn, connect_timeout=30)
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        con.close()


def _raum_id(scon: sqlite3.Connection, raum_code: str, typ: str, quelle_id: int) -> int:
    scon.execute(
        "INSERT INTO raumeinheit (raum_code, typ, name, quelle_id) VALUES (?,?,?,?) "
        "ON CONFLICT(raum_code) DO NOTHING",
        (raum_code, typ, raum_code, quelle_id),
    )
    return scon.execute("SELECT id FROM raumeinheit WHERE raum_code = ?", (raum_code,)).fetchone()[0]


def import_tech(
    scon: sqlite3.Connection, tech_code: str, rows: list[tuple],
    raum_typ: str, base_year: int, tech_id: int, quelle_id: int,
) -> tuple[int, int]:
    """Schreibt Zubau + kumulierten Bestand (historie) und Basisjahr-Snapshot (bestand_ist)."""
    # nach Raum gruppieren, je Raum nach Jahr sortieren -> kumulieren
    by_raum: dict[str, list[tuple]] = {}
    for raum_code, jahr, anzahl, kw, kwh in rows:
        if jahr is None:
            continue
        by_raum.setdefault(str(raum_code), []).append(
            (int(jahr), int(anzahl or 0), float(kw or 0.0), float(kwh) if kwh is not None else None)
        )

    h_rows: list[tuple] = []   # historie
    b_rows: list[tuple] = []   # bestand_ist
    for raum_code, jahre in by_raum.items():
        rid = _raum_id(scon, raum_code, raum_typ, quelle_id)
        jahre.sort()
        cum_n = cum_kw = 0
        cum_kwh = 0.0
        has_kwh = False
        for jahr, n, kw, kwh in jahre:
            # Zubau
            h_rows.append((tech_id, rid, jahr, float(n), "zubau", "Anlagen", quelle_id))
            h_rows.append((tech_id, rid, jahr, kw, "zubau", "kW", quelle_id))
            if kwh is not None:
                h_rows.append((tech_id, rid, jahr, kwh, "zubau", "kWh", quelle_id))
                cum_kwh += kwh
                has_kwh = True
            # kumulierter Bestand
            cum_n += n
            cum_kw += kw
            h_rows.append((tech_id, rid, jahr, float(cum_n), "bestand", "Anlagen", quelle_id))
            h_rows.append((tech_id, rid, jahr, cum_kw, "bestand", "kW", quelle_id))
            if has_kwh:
                h_rows.append((tech_id, rid, jahr, cum_kwh, "bestand", "kWh", quelle_id))
        # Basisjahr-Snapshot (kumuliert bis base_year — rows enden bereits bei base_year)
        b_rows.append((
            tech_id, rid, base_year, cum_n, cum_kw,
            cum_kwh if has_kwh else None, quelle_id,
        ))

    scon.executemany(
        "INSERT INTO historie (technologie_id,raum_id,jahr,wert,groesse,einheit,quelle_id) "
        "VALUES (?,?,?,?,?,?,?)", h_rows,
    )
    scon.executemany(
        "INSERT INTO bestand_ist (technologie_id,raum_id,jahr,anzahl,leistung_kw,kapazitaet_kwh,quelle_id) "
        "VALUES (?,?,?,?,?,?,?)", b_rows,
    )
    return len(h_rows), len(b_rows)


def run(
    db_path: Path, dsn: str, bundesland: str, level: str, min_year: int,
    base_year: int, pv_max_kw: float, storage_max_kw: float,
    pv_nutzung: str, replace: bool,
) -> None:
    if not db_path.exists():
        raise SystemExit(f"DB nicht gefunden: {db_path} — zuerst build_db.py.")
    raum_typ, level_col = LEVEL[level]

    scon = sqlite3.connect(db_path)
    scon.execute("PRAGMA foreign_keys = ON")
    q = scon.execute("SELECT id FROM datenquelle WHERE code='mastr'").fetchone()
    if q is None:
        raise SystemExit("Datenquelle 'mastr' fehlt — Seed nicht angewandt?")
    quelle_id = q[0]
    tech_ids = dict(scon.execute("SELECT code,id FROM technologie").fetchall())

    for tech in ("pv", "batteriespeicher"):
        existing = scon.execute(
            "SELECT count(*) FROM historie WHERE technologie_id=? AND quelle_id=?",
            (tech_ids[tech], quelle_id),
        ).fetchone()[0]
        if existing and not replace:
            raise SystemExit(f"Abbruch: {tech} bereits importiert. Mit --replace ersetzen.")
        if existing and replace:
            scon.execute("DELETE FROM historie WHERE technologie_id=? AND quelle_id=?",
                         (tech_ids[tech], quelle_id))
            scon.execute("DELETE FROM bestand_ist WHERE technologie_id=? AND quelle_id=?",
                         (tech_ids[tech], quelle_id))

    params = {
        "bl": bundesland, "dmin": f"{min_year}-01-01", "dmax": f"{base_year}-12-31",
        "nutzung": pv_nutzung, "raum": bundesland,
    }
    for tech, maxkw in (("pv", pv_max_kw), ("batteriespeicher", storage_max_kw)):
        query_fn, _ = TECHS[tech]
        p = dict(params, maxkw=maxkw)
        print(f"MaStR-Abfrage: {tech} ({bundesland}, Ebene={level}, ≤{maxkw} kW) …", flush=True)
        rows = _fetch(dsn, query_fn(level_col), p)
        h, b = import_tech(scon, tech, rows, raum_typ, base_year, tech_ids[tech], quelle_id)
        scon.execute(
            "INSERT INTO import_log (quelle_id,ziel_tabelle,zeilen,skript_version,importiert_am) "
            "VALUES (?,?,?,?,?)",
            (quelle_id, f"historie/{tech}", h, VERSION, _dt.datetime.now().isoformat(timespec="seconds")),
        )
        print(f"  {tech}: {len(rows)} Aggregatzeilen → {h} historie + {b} bestand_ist")
    scon.commit()
    scon.close()
    print("Import abgeschlossen.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--dsn", default=DEFAULT_DSN, help="PostgreSQL-DSN (MaStR)")
    p.add_argument("--bundesland", default="Nordrhein-Westfalen")
    p.add_argument("--level", choices=list(LEVEL), default="nrw", help="Raum-Ebene (Default: nrw)")
    p.add_argument("--min-year", type=int, default=2000)
    p.add_argument("--base-year", type=int, default=2024, help="Basisjahr des Ist-Bestands")
    p.add_argument("--pv-max-kw", type=float, default=30.0, help="Leistungsdeckel EFH-PV (kWp)")
    p.add_argument("--storage-max-kw", type=float, default=30.0, help="Leistungsdeckel Heimspeicher (kW)")
    p.add_argument("--pv-nutzungsbereich", default="Haushalt")
    p.add_argument("--replace", action="store_true")
    args = p.parse_args(argv)
    run(args.db.resolve(), args.dsn, args.bundesland, args.level, args.min_year,
        args.base_year, args.pv_max_kw, args.storage_max_kw, args.pv_nutzungsbereich, args.replace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
