"""
pipeline/fitting.py — Schritt 1: Deterministische Projektionen.

Fittet alle 12 S-Kurven-Modelle an jede Gemeinde (DE → NLS).
Enthält zusätzlich die Sättigungsberechnung via optionaler Metadaten.

Öffentliche Funktionen:
  compute_saturation()          : C_lo / C_hi je Gemeinde
  fit_model()                   : Fit eines einzelnen Modells
  step1_deterministic_parallel(): Schritt 1 für alle Gemeinden (parallel)
"""

from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, differential_evolution
from joblib import Parallel, delayed
from tqdm import tqdm

from pv_hochlauf.core.config import DE_MAXITER, DE_POPSIZE, PROJ_END, TEST_MODE
from pv_hochlauf.core.models import ALL_MODELS, MODEL_FNS, get_bounds_and_p0


def compute_saturation(
    gemeinde_code: str,
    last_kw: float,
    metadata_df: Optional[pd.DataFrame] = None,
    default_multiplier: float = 5.0,
) -> Tuple[float, float]:
    """
    Berechnet den Sättigungsbereich [C_lo, C_hi] für eine Gemeinde.

    C_lo = aktueller Bestand (Kurve darf nicht darunter sättigen)
    C_hi = technisches Potenzial (aus Metadaten) oder C_lo × Multiplikator

    Mit Metadaten (metadata_df mit Index=Gemeindeschlüssel und Spalten):
      Dachflaeche_m2  : Nutzbare Dachfläche [m²]
      Moduleffizienz  : Systemeffizienz [kW/m²] (Standard: 0.205)

    Potenzialformel:
      C_hi [kW] = Dachflaeche_m2 × Moduleffizienz

    Parameter
    ----------
    gemeinde_code      : str            AGS der Gemeinde
    last_kw            : float          Letzter historischer Bestand [kW]
    metadata_df        : pd.DataFrame   Optional; Index = Gemeindeschlüssel
    default_multiplier : float          Fallback-Multiplikator (Standard: 5×)

    Returns
    -------
    (C_lo, C_hi) : Tuple[float, float]
    """
    C_lo = float(last_kw)

    if metadata_df is not None and gemeinde_code in metadata_df.index:
        c_hi_kwp = metadata_df.loc[gemeinde_code, "C_hi_kWp"]

        # None-Wert (unvollständige BUILDA-Daten) → Fallback
        if c_hi_kwp is None or pd.isna(c_hi_kwp):
            C_hi = C_lo * default_multiplier
            return C_lo, C_hi

        C_hi = float(np.clip(c_hi_kwp, C_lo * 2.0, None))
        return C_lo, C_hi

    C_hi = C_lo * default_multiplier
    return C_lo, C_hi


def fit_model(
    model_name: str,
    t_years: np.ndarray,
    values: np.ndarray,
    C_lo: float,
    C_hi: float,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Fittet ein S-Kurven-Modell an historische Daten (DE → NLS).

    Strategie nach Supplementary A.6:
      1. Differential Evolution → globales Optimum im Parameterraum
         (wichtig weil S-Kurven viele lokale Minima haben)
      2. NLS curve_fit (TRF) → Verfeinerung des DE-Ergebnisses

    Parameter
    ----------
    model_name : str         Name des Modells (aus ALL_MODELS)
    t_years    : np.ndarray  Zeitachse (absolute Jahreszahlen, z.B. [2000, 2001, ...])
    values     : np.ndarray  Historische kumulierte Werte [kW]
    C_lo       : float       Untergrenze für Sättigungsparameter C
    C_hi       : float       Obergrenze für Sättigungsparameter C

    Returns
    -------
    popt   : np.ndarray  Optimale Parameter
    fitted : np.ndarray  Gefittete Werte auf t_years
    r2     : float       Bestimmtheitsmaß R²
    """
    fn   = MODEL_FNS[model_name]
    z_hi = max(float(values[0]) * 0.5, 1e-3) if values[0] > 0 else 1e-3
    lb, ub, p0 = get_bounds_and_p0(model_name, C_lo, C_hi, z_hi)

    def _sse(params):
        try:
            return float(np.sum((values - fn(t_years, *params)) ** 2))
        except Exception:
            return 1e18

    # Schritt 1: Differential Evolution
    try:
        res    = differential_evolution(
            _sse, list(zip(lb, ub)), seed=42,
            maxiter=DE_MAXITER, tol=1e-7, polish=False,
            popsize=DE_POPSIZE, workers=1,
        )
        p_init = res.x
    except Exception:
        p_init = p0

    # Schritt 2: NLS-Verfeinerung (Trust Region Reflective)
    try:
        popt, _ = curve_fit(
            fn, t_years, values,
            p0=p_init, bounds=(lb, ub),
            maxfev=8000, method="trf",
        )
    except Exception:
        popt = np.array(p_init)

    fitted = fn(t_years, *popt)
    ss_res = float(np.sum((values - fitted) ** 2))
    ss_tot = float(np.sum((values - values.mean()) ** 2))
    r2     = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return popt, fitted, r2


def _fit_single_gemeinde(
    gemeinde: str,
    ts: pd.DataFrame,
    metric: str,
    metadata_df: Optional[pd.DataFrame],
    proj_end: int,
) -> Tuple[str, Dict]:
    """
    Hilfsfunktion für die parallele Verarbeitung einer einzelnen Gemeinde.
    Fittet alle 12 Modelle und berechnet deterministische Projektionen.

    Parameter
    ----------
    gemeinde   : str            Gemeindename
    ts         : pd.DataFrame   Zeitreihe der Gemeinde
    metric     : str            Spaltenname (z.B. 'kW_kum')
    metadata_df: pd.DataFrame   Optionale Metadaten für Sättigungsberechnung
    proj_end   : int            Letztes Projektionsjahr

    Returns
    -------
    (gemeinde, det_proj_eintrag) : Tuple
    """
    t_years = ts.index.values.astype(float)
    values  = ts[metric].values.astype(float)
    t_proj  = np.arange(t_years[0], proj_end + 1, dtype=float)
    C_lo, C_hi = compute_saturation(gemeinde, values[-1], metadata_df)

    models_dict = {}
    for mname in ALL_MODELS:
        try:
            popt, fitted, r2 = fit_model(mname, t_years, values, C_lo, C_hi)
            # Deterministische Projektion über gesamten Zeitraum
            proj = MODEL_FNS[mname](t_proj, *popt)
            proj = np.maximum.accumulate(np.clip(proj, 0, None))
        except Exception:
            # Fallback: flache Linie auf letztem historischen Wert
            popt   = None
            fitted = np.full(len(t_years), values[-1])
            r2     = 0.0
            proj   = np.full(len(t_proj), values[-1])

        models_dict[mname] = {
            "popt":   popt,
            "fitted": fitted,
            "r2":     r2,
            "proj":   proj,
        }

    entry = {
        "t_hist":   t_years,
        "v_hist":   values,
        "t_proj":   t_proj,
        "C_lo":     C_lo,
        "C_hi":     C_hi,
        "models":   models_dict,
        "excluded": False,   # Marker: individuelle Fits vorhanden
    }
    return gemeinde, entry


def step1_deterministic_parallel(
    gemeinde_ts: Dict[str, pd.DataFrame],
    metric: str = "kW_kum",
    metadata_df: Optional[pd.DataFrame] = None,
    proj_end: int = PROJ_END,
) -> Dict[str, Dict]:
    """
    Schritt 1 nach Zielonka et al.: Deterministische Projektionen für alle Gemeinden.

    Fittet alle 12 S-Kurven-Modelle je Gemeinde (parallel auf allen CPU-Kernen).
    Optimierung: Differential Evolution → NLS (nach Supplementary A.6).

    Parameter
    ----------
    gemeinde_ts : dict            Ausgabe von filter_timeseries() (nur valide Gemeinden)
    metric      : str             Spaltenname (Standard: 'kW_kum')
    metadata_df : pd.DataFrame    Optional: Metadaten für Sättigungsberechnung
    proj_end    : int             Letztes Projektionsjahr (Standard: 2050)

    Returns
    -------
    det_proj : dict
        Gemeindename → {
          't_hist'  : np.ndarray   historische Jahre
          'v_hist'  : np.ndarray   historische Werte [kW]
          't_proj'  : np.ndarray   Projektionsjahre
          'C_lo'    : float        Sättigungs-Untergrenze
          'C_hi'    : float        Sättigungs-Obergrenze
          'models'  : dict         mname → {popt, fitted, r2, proj}
          'excluded': bool         False = individueller Fit vorhanden
        }
    """
    print(f"  Schritt 1 (Parallel): {len(gemeinde_ts):,} Gemeinden × {len(ALL_MODELS)} Modelle")

    results = Parallel(n_jobs=-1)(
        delayed(_fit_single_gemeinde)(g, ts, metric, metadata_df, proj_end)
        for g, ts in tqdm(gemeinde_ts.items(), desc="Gefittet")
    )
    return dict(results)
