"""io/db_adapter.py — Phase-1-Integration (AP 3.1).

Lädt die MaStR-PV-Rohdaten aus dem **Open-Energy-Data-Server** (OEDS, PostgreSQL,
Schema ``mastr-2025``) statt aus Jans lokalem Pickle. Liefert denselben
DataFrame-Shape wie ``io.database.load_mastr_data()``, sodass
``io.database.prepare_timeseries()`` unverändert weiterläuft.

Gleiche Quelle wie ``hochlauf_model/db/import_mastr.py`` — hier aber **roh und je
Gemeinde** (die Zielonka-Peer-Similarity braucht alle Gemeinden einzeln, nicht das
Aggregat der ``historie``-Tabelle).

    from pv_hochlauf.io.db_adapter import load_mastr_pv
    df = load_mastr_pv(bundesland="Nordrhein-Westfalen")
"""
from __future__ import annotations

import psycopg2
import pandas as pd

DEFAULT_DSN = "postgresql://readonly:readonly@timescale.nowum.fh-aachen.de:5432/opendata"
SCHEMA = "mastr-2025"

# Spalten, die prepare_timeseries() + cities_dict benötigen.
COLUMNS = [
    "Inbetriebnahmedatum",
    "GeplantesInbetriebnahmedatum",
    "Postleitzahl",
    "Gemeinde",
    "Gemeindeschluessel",
    "Bruttoleistung",
    "Nettonennleistung",
    "Nutzungsbereich",
    "EinheitBetriebsstatus",
]


def load_mastr_pv(
    dsn: str = DEFAULT_DSN,
    bundesland: str | None = "Nordrhein-Westfalen",
    gemeindeschluessel: list[str] | None = None,
    timeout: int = 120,
) -> pd.DataFrame:
    """MaStR-PV (``solar_extended``) als Roh-DataFrame.

    Parameter
    ----------
    bundesland         : optionaler Bundesland-Filter (Default NRW; None = ganz DE)
    gemeindeschluessel : optionale AGS-Liste (überschreibt bundesland-Filter nicht,
                         sondern verengt zusätzlich — für Tests)
    """
    cols = ", ".join(f'"{c}"' for c in COLUMNS)
    where, params = [], {}
    if bundesland is not None:
        where.append('"Bundesland" = %(bl)s')
        params["bl"] = bundesland
    if gemeindeschluessel:
        where.append('"Gemeindeschluessel" = ANY(%(ags)s)')
        params["ags"] = list(gemeindeschluessel)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f'SELECT {cols} FROM "{SCHEMA}".solar_extended{clause}'

    con = psycopg2.connect(dsn, connect_timeout=timeout)
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            names = [d[0] for d in cur.description]
    finally:
        con.close()
    df = pd.DataFrame(rows, columns=names)
    print(f"OEDS: {len(df):,} PV-Anlagen geladen"
          f"{f' (Bundesland={bundesland})' if bundesland else ''}.")
    return df
