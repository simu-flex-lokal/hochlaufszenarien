"""
io/database.py — Datenbankanbindung und Datenaufbereitung.

Funktionen:
  load_mastr_data()    : Lädt EinheitenSolar aus PostgreSQL-Datenbank
  load_local_data()    : Lädt gespeicherte Parquet/CSV-Datei (lokal)
  prepare_timeseries() : Bereinigt Rohdaten → jährliche Zeitreihen je Gemeinde
  filter_timeseries()  : Filtert ungeeignete Zeitreihen (nach Supp. A.5)
"""

import psycopg2
from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd

from pv_hochlauf.core.config import (YEAR_MIN, YEAR_MAX, MIN_TRAIN_YRS,
    FILTER_RESIDENTIAL, MAX_KWP_RESIDENTIAL,
    RESIDENTIAL_NUTZUNG, INCLUDE_NONE_NUTZUNG,
)


def load_mastr_data(
    host: str     = "YOUR_HOST",
    port: int     = 5432,
    dbname: str   = "YOUR_DB",
    user: str     = "YOUR_USER",
    password: str = "YOUR_PASSWORD",
) -> pd.DataFrame:
    """
    Lädt EinheitenSolar aus der MaStR-PostgreSQL-Datenbank.

    Spalten: Registrierungsdatum, Inbetriebnahmedatum,
             GeplantesInbetriebnahmedatum, Postleitzahl,
             Gemeinde, Gemeindeschluessel, Bruttoleistung, 
             Nettonennleistung, Nutzungsbereich
             Nettonennleistung, Nutzungsbereich,
             EinheitBetriebsstatus

    Parameter
    ----------
    host, port, dbname, user, password : DB-Verbindungsparameter

    Returns
    -------
    pd.DataFrame mit den Rohdaten
    """

    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, password=password,
    )
    with conn.cursor() as cur:
        cur.execute("""
            SELECT "Registrierungsdatum",
                   "Inbetriebnahmedatum",
                   "GeplantesInbetriebnahmedatum",
                   "Postleitzahl",
                   "Gemeinde",
                   "Gemeindeschluessel",
                   "Bruttoleistung",
                   "Nettonennleistung",
                   "Nutzungsbereich"
                   "Nutzungsbereich",
                   "EinheitBetriebsstatus"
            FROM "mastr-2025".solar_extended
        """)
        rows    = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    conn.close()

    df = pd.DataFrame(rows, columns=columns)
    print(f"Geladen: {len(df):,} Anlagen aus der Datenbank.")
    return df


def filter_residential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtert den DataFrame optional auf Wohngebäude-PV-Anlagen.

    Aktiviert durch FILTER_RESIDENTIAL=True in config.py.
    Zwei Filterkriterien werden kombiniert:

    1. Nutzungsbereich-Filter:
       Nur Anlagen mit Nutzungsbereich in RESIDENTIAL_NUTZUNG werden behalten.
       Einträge mit Nutzungsbereich=None werden je nach INCLUDE_NONE_NUTZUNG
       ein- oder ausgeschlossen.

    2. Größenfilter:
       Anlagen mit Nettonennleistung > MAX_KWP_RESIDENTIAL [kWp] (in config.py
       festgelegt) werden als gewerblich/industriell eingestuft und 
       herausgefiltert, wenn Nutzungsbereich=None.

    Parameter
    ----------
    df : pd.DataFrame  Rohdaten (muss Spalten 'Nutzungsbereich' und
                        'Nettonennleistung' enthalten)

    Returns
    -------
    pd.DataFrame  gefilterter DataFrame
    """
    if not FILTER_RESIDENTIAL:
        return df

    n_before = len(df)

    # --- Nutzungsbereich-Filter ---
    if "Nutzungsbereich" in df.columns:
        # Maske für erlaubte Nutzungsbereiche
        mask_nutzung = df["Nutzungsbereich"].isin(RESIDENTIAL_NUTZUNG)
        if INCLUDE_NONE_NUTZUNG:
            # None-Einträge zusätzlich einschließen
            mask_nutzung = mask_nutzung | df["Nutzungsbereich"].isna()
        df = df[mask_nutzung]
        n_nutzung = n_before - len(df)
        print(f"  Nutzungsbereich-Filter: {n_nutzung:,} Anlagen entfernt ")
    else:
        print("  HINWEIS: Spalte 'Nutzungsbereich' nicht vorhanden "
              "→ Nutzungsbereich-Filter übersprungen.")

    # --- Größenfilter ---
    kw_col = pd.to_numeric(df["Nettonennleistung"], errors="coerce").fillna(0)
    # Nettonennleistung ist in kW gespeichert → direkt mit MAX_KWP_RESIDENTIAL vergleichen
    mask_size = ~((kw_col > MAX_KWP_RESIDENTIAL) & df["Nutzungsbereich"].isna())
    n_size    = len(df) - mask_size.sum()
    df        = df[mask_size]
    print(f"  Größenfilter (> {MAX_KWP_RESIDENTIAL} kWp) für 'Nutzungsbereich' = None: {n_size:,} Anlagen entfernt")

    n_removed = n_before - len(df)
    print(f"  Wohngebäude-Filter gesamt: {n_removed:,} von {n_before:,} entfernt "
          f"→ {len(df):,} Anlagen verbleiben ({len(df)/n_before*100:.1f}%)")
    return df


def prepare_timeseries(
    df: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Bereinigt Rohdaten und erzeugt jährliche kumulative Zeitreihen je Gemeinde.

    Verarbeitungsreihenfolge:
      1. Optionaler Wohngebäude-Filter (filter_residential)
      2. Datumlogik: Inbetriebnahmedatum → GeplantesInbetriebnahmedatum → verwerfen
      3. Betriebsstatus: stillgelegte Anlagen herausfiltern
      4. Jahresfilter: YEAR_MIN - YEAR_MAX
      5. Leistungsbereinigung: negative/fehlende Werte → 0
      6. Kumulative Jahresreihen je Gemeinde

    Primärmetrik  : kW_kum      — kumulierte Nettonennleistung [kW]
    Sekundärmetrik: Anlagen_kum — kumulierte Anlagenanzahl

    Parameter
    ----------
    df : pd.DataFrame  Rohdaten aus load_mastr_data() oder load_local_data()

    Returns
    -------
    dict: Gemeindename → pd.DataFrame(Index=Jahr, Spalten=[kW_kum, Anlagen_kum])
    """
    df = df.copy()

    # Schritt 1: Optionaler Wohngebäude-Filter
    if FILTER_RESIDENTIAL:
        print("  Wohngebäude-Filter aktiv (FILTER_RESIDENTIAL=True):")
        df = filter_residential(df)
    else:
        print("  Wohngebäude-Filter inaktiv → alle Anlagen werden verwendet.")

    # Datumspalten parsen
    for col in ["Inbetriebnahmedatum", "GeplantesInbetriebnahmedatum"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Fallback-Logik: Inbetriebnahme → Geplant → verwerfen
    df["Datum"] = df["Inbetriebnahmedatum"].fillna(df["GeplantesInbetriebnahmedatum"])

    n_before = len(df)
    df = df.dropna(subset=["Datum"])
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"  Ohne verwertbares Datum verworfen: {n_dropped:,} "
              f"({n_dropped / n_before * 100:.1f}%)")

    # Betriebsstatus: stillgelegte Anlagen werden herausgefiltert
    df = df[~(df["EinheitBetriebsstatus"]=='Endgültig stillgelegt')]

    # Jahresfilter: [YEAR_MIN, YEAR_MAX]
    df["Jahr"] = df["Datum"].dt.year
    mask_inv = (df["Jahr"] < YEAR_MIN) | (df["Jahr"] > YEAR_MAX)
    if mask_inv.sum():
        top = df.loc[mask_inv, "Jahr"].value_counts().head(5).to_dict()
        print(f"  Daten nach Jahresfilter verworfen: {mask_inv.sum():,} "
              f"(Top-5: {top})")
        df = df[~mask_inv]

    # Leistung bereinigen
    df["Nettonennleistung"] = (
        pd.to_numeric(df["Nettonennleistung"], errors="coerce")
        .clip(lower=0)
        .fillna(0)
    )

    # Jährliche Aggregation je Gemeinde
    gemeinde_ts: Dict[str, pd.DataFrame] = {}
    for gemeinde, grp in df.groupby("Gemeindeschluessel"):
        ts = (
            grp.groupby("Jahr")
               .agg(kW=("Nettonennleistung", "sum"), Anlagen=("Datum", "count"))
               .sort_index()
        )
        # Lückenlose Jahresreihe sicherstellen
        full_idx = pd.RangeIndex(ts.index.min(), ts.index.max() + 1)
        ts = ts.reindex(full_idx, fill_value=0)
        ts["kW_kum"]      = ts["kW"].cumsum().astype(float)
        ts["Anlagen_kum"] = ts["Anlagen"].cumsum().astype(float)
        gemeinde_ts[gemeinde] = ts[["kW_kum", "Anlagen_kum"]]

    total_gw = sum(ts["kW_kum"].iloc[-1] for ts in gemeinde_ts.values()) / 1e6
    print(f"  Gemeinden:       {len(gemeinde_ts):,}")
    print(f"  Leistung gesamt: {total_gw:.2f} GW")
    print(f"  Zeitraum:        {df['Jahr'].min()} – {df['Jahr'].max()}")
    return gemeinde_ts


def filter_timeseries(
    gemeinde_ts: Dict[str, pd.DataFrame],
    metric: str = "kW_kum",
    min_years: int = MIN_TRAIN_YRS,
) -> Tuple[Dict, Dict]:
    """
    Filtert Gemeinden mit ungeeigneten Zeitreihen nach Zielonka Supp. A.5.

    Ausschlusskriterien:
      1. Weniger als min_years Datenpunkte → kein stabiler Fit möglich
      2. Letzter Wert = 0 → kein PV-Bestand vorhanden
      3. Einer der letzten 3 Werte = 0 → Datenlücke / MaStR-Meldeverzug
      4. Letzte 5 Werte identisch → Stagnation (quasi-statische Reihe)
      5. Einbruch ≥ 50% in einem Jahr → Ummeldung / Datenfehler

    Parameter
    ----------
    gemeinde_ts : dict   Ausgabe von prepare_timeseries()
    metric      : str    Spalte für den Vergleich (Standard: 'kW_kum')
    min_years   : int    Mindestlänge der Zeitreihe

    Returns
    -------
    valid    : dict  geeignete Gemeinden (für Schritt 1-4)
    excluded : dict  ausgeschlossene Gemeinden (erhalten Ersatzprojektionen)
    """
    valid: Dict[str, pd.DataFrame]    = {}
    excluded: Dict[str, pd.DataFrame] = {}

    for name, ts in gemeinde_ts.items():
        v = ts[metric].values

        if len(v) < min_years:
            excluded[name] = ts; continue
        if v[-1] == 0:
            excluded[name] = ts; continue
        if any(v[-3:] == 0):
            excluded[name] = ts; continue
        if len(v) >= 5 and np.all(v[-5:] == v[-5]):
            excluded[name] = ts; continue
        # Einbruch ≥ 50% in einem Jahr (z.B. durch Ummeldung)
        if np.any(np.diff(v) < -0.5 * v[:-1]):
            excluded[name] = ts; continue

        valid[name] = ts

    print(f"Zeitreihenfilter: {len(valid):,} gültig / {len(excluded):,} ausgeschlossen")
    return valid, excluded