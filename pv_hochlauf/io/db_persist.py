"""io/db_persist.py — Phase-1-Persistenz (AP 3.1).

Schreibt das Zielonka-Ensemble-Band in unsere SQLite-DB (Tabelle
``diffusion_ensemble``) — die neue produktive Zeitkomponente (Komponente C),
die die Einzel-Logistik (``components/diffusion.py`` / ``diffusion_fit``) ablöst.

    from pv_hochlauf.io.db_persist import persist_from_band_csv
    persist_from_band_csv(db, "05374040", "Reichshof", Path("…/band_05374040.csv"),
                          meta={"n_similar": 121, ...})
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from pathlib import Path

import pandas as pd

DEFAULT_DB = Path(__file__).resolve().parents[1] / "hochlauf.sqlite"
DEFAULT_STUETZJAHRE = (2025, 2030, 2035, 2040, 2045, 2050)
QUANTILE_COLS = {0.05: "p05_MWp", 0.25: "p25_MWp", 0.50: "p50_MWp", 0.75: "p75_MWp", 0.95: "p95_MWp"}


def _raum_id(con, ags: str, name: str, quelle_id: int | None) -> int:
    con.execute(
        "INSERT INTO raumeinheit (raum_code, typ, name, quelle_id) VALUES (?,?,?,?) "
        "ON CONFLICT(raum_code) DO UPDATE SET name=excluded.name",
        (ags, "gemeinde", name, quelle_id))
    return con.execute("SELECT id FROM raumeinheit WHERE raum_code=?", (ags,)).fetchone()[0]


def persist_band(
    db_path: Path,
    ags: str,
    gemeinde_name: str,
    band: pd.DataFrame,
    *,
    technologie: str = "pv",
    einheit: str = "MWp",
    stuetzjahre=DEFAULT_STUETZJAHRE,
    meta: dict | None = None,
    quelle_code: str = "mastr",
    replace: bool = True,
) -> int:
    """Schreibt das Quantil-Band (Spalten jahr + p05_MWp…p95_MWp) in diffusion_ensemble."""
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    tech = con.execute("SELECT id FROM technologie WHERE code=?", (technologie,)).fetchone()
    if tech is None:
        raise SystemExit(f"Technologie {technologie} unbekannt.")
    tech_id = tech[0]
    q = con.execute("SELECT id FROM datenquelle WHERE code=?", (quelle_code,)).fetchone()
    quelle_id = q[0] if q else None
    rid = _raum_id(con, ags, gemeinde_name, quelle_id)

    if replace:
        con.execute("DELETE FROM diffusion_ensemble WHERE technologie_id=? AND raum_id=? AND einheit=?",
                    (tech_id, rid, einheit))
    by_year = band.set_index("jahr")
    now = _dt.datetime.now().isoformat(timespec="seconds")
    meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
    n = 0
    for yr in stuetzjahre:
        if yr not in by_year.index:
            continue
        row = by_year.loc[yr]
        for quant, col in QUANTILE_COLS.items():
            con.execute(
                "INSERT INTO diffusion_ensemble "
                "(technologie_id,raum_id,stuetzjahr,quantil,wert,einheit,modell,meta_json,quelle_id,erstellt_am) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (tech_id, rid, int(yr), quant, float(row[col]), einheit,
                 "zielonka-ensemble", meta_json, quelle_id, now))
            n += 1
    con.commit()
    con.close()
    print(f"diffusion_ensemble: {n} Zeilen für {gemeinde_name} ({ags}) "
          f"[{technologie}/{einheit}, {len(stuetzjahre)} Stützjahre × {len(QUANTILE_COLS)} Quantile].")
    return n


def persist_from_band_csv(db_path, ags, gemeinde_name, band_csv: Path, **kw) -> int:
    return persist_band(db_path, ags, gemeinde_name, pd.read_csv(band_csv), **kw)
