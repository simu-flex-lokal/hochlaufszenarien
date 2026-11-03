"""
io/export.py — CSV-Export der Ergebnisse.

Öffentliche Funktionen:
  export_gemeinde_csv() : Quantile + Pfade für eine Gemeinde
  export_national_csv() : Nationale Aggregation
"""

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from pv_hochlauf.core.config import OUT_CSV, QUANTILES


def export_gemeinde_csv(
    gemeinde: str,
    ensemble: Dict,
    cities_dict: Dict,
) -> None:
    """
    Exportiert Quantile und Szenariopfade einer Gemeinde als CSV.

    Dateien:
      quantile_<Gemeinde>.csv : Quantile je Jahr [kW]
      pfade_<Gemeinde>.csv    : Szenariopfade je Jahr [MWp]

    Parameter
    ----------
    gemeinde    : str   Gemeindeschlüssel
    ensemble    : dict  Ergebnis aus Schritt 4 (enthält 't_proj', 'quantiles', 'paths')
    cities_dict : list  Enthält den Gemeindenamen zum Gemeindeschlüssel für die Speicherung
    """
    d      = ensemble[gemeinde]
    t_proj = d["t_proj"].astype(int)
    qs     = d["quantiles"]
    safe   = cities_dict[gemeinde]["Gemeinde"].replace(" ", "_").replace("/", "-")

    # Quantile-CSV
    rows = []
    for i, yr in enumerate(t_proj):
        row = {"Jahr": int(yr)}
        for q in sorted(qs.keys()):
            row[f"P{int(q * 100):02d}_kW"] = round(float(qs[q][i]), 2)
        rows.append(row)
    path_q = OUT_CSV / f"quantile_{safe}.csv"
    pd.DataFrame(rows).to_csv(path_q, index=False)
    print(f"  → {path_q}")

    # Pfade-CSV (in MWp für bessere Lesbarkeit)
    df_paths = pd.DataFrame(
        d["paths"].T / 1000,
        index=t_proj,
        columns=[f"Pfad_{i + 1:03d}" for i in range(d["paths"].shape[0])],
    )
    df_paths.index.name = "Jahr"
    path_p = OUT_CSV / f"pfade_{safe}.csv"
    df_paths.to_csv(path_p)
    print(f"  → {path_p}")


def export_national_csv(
    nat_q: Dict,
    nat_paths: np.ndarray,
    years: np.ndarray,
) -> None:
    """
    Exportiert nationale Aggregation als CSV.

    Dateien:
      quantile_national.csv : Quantile je Jahr [GW]
      pfade_national.csv    : Szenariopfade je Jahr [GW]

    Parameter
    ----------
    nat_q     : dict         q → pd.Series [kW]
    nat_paths : np.ndarray   (n_paths × n_jahre) [kW]
    years     : np.ndarray   Jahresarray
    """
    # Quantile
    rows = []
    for i, yr in enumerate(years):
        row = {"Jahr": int(yr)}
        for q, series in nat_q.items():
            row[f"P{int(q * 100):02d}_GW"] = round(float(series.iloc[i]) / 1e6, 4)
        rows.append(row)
    path_q = OUT_CSV / "quantile_national.csv"
    pd.DataFrame(rows).to_csv(path_q, index=False)
    print(f"  → {path_q}")

    # Pfade
    df_paths = pd.DataFrame(
        nat_paths.T / 1e6,
        index=years,
        columns=[f"Pfad_{i + 1:03d}" for i in range(nat_paths.shape[0])],
    )
    df_paths.index.name = "Jahr"
    path_p = OUT_CSV / "pfade_national.csv"
    df_paths.to_csv(path_p)
    print(f"  → {path_p}")
