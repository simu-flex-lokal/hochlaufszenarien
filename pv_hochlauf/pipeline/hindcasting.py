"""
pipeline/hindcasting.py — Schritt 3: Hindcasting und Modellgewichte.

Bewertet jedes Modell durch iteratives Backtesting (MAPE + WIS).
Gewichte werden proportional zu 1/WIS² vergeben (nach Zielonka et al.).

Öffentliche Funktionen:
  interval_score()        : Interval Score für ein Konfidenzintervall
  hindcast_single_model() : MAPE + WIS für ein Modell auf einer Zeitreihe
  step3_hindcasting()     : Schritt 3 für alle Zielgemeinden (parallel)
"""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import warnings

import numpy as np
from scipy.optimize import curve_fit, OptimizeWarning
from joblib import Parallel, delayed
from tqdm import tqdm

from pv_hochlauf.core.config import (
    MIN_TRAIN_YRS, MAX_AHEAD_YRS, SIMILARITY_PCT, QUANTILES, HINDCAST_MAX_SIMILAR
)
from pv_hochlauf.core.models import ALL_MODELS, MODEL_FNS, get_bounds_and_p0
from pv_hochlauf.pipeline.fitting import fit_model
from pv_hochlauf.pipeline.probabilistic import normalize_ts, euclidean_dist


def interval_score(
    lower: float,
    upper: float,
    actual: float,
    alpha: float,
) -> float:
    """
    Interval Score (IS) für ein einzelnes (1-alpha)-Konfidenzintervall.

    IS_alpha = (upper - lower)                             [Sharpness]
               + (2/alpha) * max(lower - actual, 0)         [Calibration: Unterschreitung]
               + (2/alpha) * max(actual - upper, 0)         [Calibration: Überschreitung]

    Parameter
    ----------
    lower, upper : float  Intervallgrenzen
    actual       : float  Tatsächlicher Wert
    alpha        : float  Signifikanzniveau (alpha = 1 - Konfidenzniveau)

    Returns
    -------
    float  Interval Score
    """
    width   = upper - lower
    penalty = (2 / alpha) * max(lower - actual, 0) + \
              (2 / alpha) * max(actual - upper,  0)
    return float(width + penalty)


def _wis_from_quantile_dict(
    q_dict: Dict[float, float],
    quantiles_sorted: List[float],
    actual: float,
) -> Tuple[float, float]:
    """
    MAPE und WIS für einen einzelnen Evaluationspunkt aus einem Satz
    von Quantilwerten.

    Parameter
    ----------
    q_dict           : dict  q → float  Quantilwerte für dieses Jahr
    quantiles_sorted : list  Sortierte Quantilwerte, muss 0.50 enthalten
    actual           : float Tatsächlicher Wert

    Returns
    -------
    (mape, wis) : Tuple[float, float]
    """
    median_pred = q_dict[0.50]
    mape = abs(median_pred - actual) / actual * 100

    qs      = quantiles_sorted
    mid     = qs.index(0.50)
    n_pairs = mid

    median_term = 0.5 * abs(actual - median_pred)
    if n_pairs == 0:
        return mape, median_term * 2   # entspricht |actual - median|

    wis_sum = 0.0
    for i in range(n_pairs):
        q_lo, q_hi = qs[i], qs[-(i + 1)]
        alpha = max(1.0 - (q_hi - q_lo), 1e-6)
        lo, hi = q_dict[q_lo], q_dict[q_hi]
        wis_sum += (alpha / 2) * interval_score(lo, hi, actual, alpha)

    wis = (median_term + wis_sum) / (n_pairs + 0.5)
    return mape, wis


def _fit_warmstart(
    model_name: str,
    t_tr: np.ndarray,
    v_tr: np.ndarray,
    C_hi_static: float,
    popt_prev: Optional[np.ndarray],
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Fittet ein Modell auf einen Datenausschnitt.

    Verwendet einen Warmstart (reine NLS) wenn ein Ergebnis aus einem
    vorherigen Split vorliegt, da sich zwischen zwei Splits
    nur ein einziger Datenpunkt ändert und der vorherige Fit fast immer
    schon sehr nah am neuen Optimum liegt. Ohne Vorergebnis wird ein
    vollständiger Fit (Differential Evolution → NLS) durchgeführt.

    Parameter
    ----------
    model_name  : str                Modellname
    t_tr, v_tr  : np.ndarray         Trunkierte Trainingsdaten
    C_hi_static : float              Statische obere Sättigungsgrenze (aus
                                     Schritt 1, z. B. technisches Potenzial)
    popt_prev   : np.ndarray | None  Ergebnis des vorherigen Splits

    Returns
    -------
    (popt, fitted) : Tuple[np.ndarray | None, np.ndarray | None]
                     None bei Fitfehler
    """
    fn = MODEL_FNS[model_name]
    C_lo_loc = max(float(v_tr[-1]), 1e-3)
    C_hi_loc = max(C_hi_static, C_lo_loc * 3.0)
    z_hi     = max(float(v_tr[0]) * 0.5, 1e-3) if v_tr[0] > 0 else 1e-3
    lb, ub, _ = get_bounds_and_p0(model_name, C_lo_loc, C_hi_loc, z_hi)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            if popt_prev is None:
                popt, fitted, _ = fit_model(
                    model_name, t_tr, v_tr, C_lo_loc, C_hi_loc)
            else:
                p0_warm = np.clip(popt_prev, lb, ub)
                popt, _ = curve_fit(
                    fn, t_tr, v_tr, p0=p0_warm,
                    bounds=(lb, ub), maxfev=2000, method="trf")
                fitted = fn(t_tr, *popt)
        return popt, fitted
    except Exception:
        return None, None


def hindcast_single_model(
    model_name: str,
    gemeinde: str,
    det_proj: Dict,
    min_train: int = MIN_TRAIN_YRS,
    max_ahead: int = MAX_AHEAD_YRS,
    similarity_pct: float = SIMILARITY_PCT,
    quantiles: List[float] = QUANTILES,
) -> Tuple[float, float]:
    """
    Für jeden Split (Trainingsjahr Y):
      1. Modell wird für die Zielgemeinde auf Daten bis Y neu gefittet
      2. Ähnliche Referenzgemeinden werden anhand ihrer historischen Werte bis Y
         gesucht (keine Zukunftsinformation), diese werden ebenfalls nur
         auf ihre Daten bis Y gefittet und für die Folgejahre projiziert.
      3. Die normierten Projektionen der ähnlichen Referenzgemeinden
         ergeben ein Quantilband für die Zielgemeinde ab Y.
      4. MAPE (Median) und WIS (Quantilpaare) werden gegen die
         tatsächlichen Realwerte der Zielgemeinde ausgewertet.

    Parameter
    ----------
    model_name      : str    Modellname
    gemeinde        : str    Zielgemeinde
    det_proj        : dict   Ergebnis aus Schritt 1 für ALLE Gemeinden
                              (liefert t_hist, v_hist, C_hi je Gemeinde als
                              Rohdaten- und Bounds-Quelle)
    min_train       : int    Erster Split-Zeitpunkt (Anzahl Trainingsjahre)
    max_ahead       : int    Maximaler Vorhersagehorizont je Split
    similarity_pct  : float  Perzentil-Schwellenwert für Ähnlichkeit
    quantiles       : list   Zu berechnende Quantile (muss 0.50 enthalten)

    Returns
    -------
    (mean_mape, mean_wis) : Tuple[float, float]
    """
    quantiles_sorted = sorted(quantiles)
    if 0.50 not in quantiles_sorted:
        raise ValueError("quantiles muss den Median (0.50) enthalten.")

    d_target   = det_proj[gemeinde]
    t_hist     = d_target["t_hist"]
    v_hist     = d_target["v_hist"]
    C_hi_stat  = d_target["C_hi"]
    n          = len(t_hist)

    all_gemeinden = [g for g in det_proj if g != gemeinde]

    mapes: List[float] = []
    wiss:  List[float] = []

    # Warmstart-Zustände: je Modell für die Zielgemeinde, je Referenzgemeinde
    # (über alle Splits hinweg persistent, da sich Trainingsdaten nur
    # inkrementell verlängern)
    popt_prev_target: Optional[np.ndarray] = None
    popt_prev_ref: Dict[str, Optional[np.ndarray]] = defaultdict(lambda: None)

    for n_train in range(min_train, n):
        Y      = t_hist[n_train - 1]          # letztes Trainingsjahr
        t_tr   = t_hist[:n_train]
        v_tr   = v_hist[:n_train]

        if v_tr[-1] <= 0:
            continue

        # --- Schritt 1: Zielgemeinde neu fitten ---
        popt_t, fitted_t = _fit_warmstart(
            model_name, t_tr, v_tr, C_hi_stat, popt_prev_target)
        if popt_t is None:
            popt_prev_target = None
            continue
        popt_prev_target = popt_t

        # --- Schritt 2: Ähnliche Referenzgemeinden suchen ---
        # Nur historische Werte bis Jahr Y verwenden
        nh_target_trunc = normalize_ts(v_tr)

        dists = []
        candidates = []
        for g2 in all_gemeinden:
            d2     = det_proj[g2]
            t2     = d2["t_hist"]
            v2     = d2["v_hist"]
            mask2  = t2 <= Y
            if mask2.sum() < min_train:
                continue
            v2_tr = v2[mask2]
            if v2_tr[-1] <= 0:
                continue
            nh2 = normalize_ts(v2_tr)
            dists.append(euclidean_dist(nh_target_trunc, nh2))
            candidates.append(g2)

        if not candidates:
            continue

        dists = np.array(dists)
        nonzero = dists[dists > 0]
        threshold = np.percentile(nonzero, similarity_pct) if len(nonzero) > 0 else 0.0
        similar = [candidates[i] for i, d in enumerate(dists) if d <= threshold]
        if len(similar) < 3:
            similar = [candidates[i] for i in np.argsort(dists)[:3]]
        if HINDCAST_MAX_SIMILAR is not None and len(similar) > HINDCAST_MAX_SIMILAR:
            # Zufällige Teilmenge der ähnlichsten begrenzen (Laufzeitschutz)
            rng = np.random.default_rng(abs(hash((gemeinde, model_name, int(Y)))) % (2**32))
            similar = list(rng.choice(similar, size=HINDCAST_MAX_SIMILAR, replace=False))


        # --- Referenzgemeinden trunkiert fitten und projizieren ---
        ahead_years = Y + np.arange(1, max_ahead + 1)
        ref_norm_curves = []

        for g2 in similar:
            d2    = det_proj[g2]
            t2    = d2["t_hist"]
            v2    = d2["v_hist"]
            mask2 = t2 <= Y
            t2_tr = t2[mask2]
            v2_tr = v2[mask2]
            if v2_tr[-1] <= 0:
                continue

            popt2, _ = _fit_warmstart(
                model_name, t2_tr, v2_tr, d2["C_hi"], popt_prev_ref[g2])
            if popt2 is None:
                popt_prev_ref[g2] = None
                continue
            popt_prev_ref[g2] = popt2

            try:
                proj2 = MODEL_FNS[model_name](ahead_years, *popt2)
            except Exception:
                continue
            ref_norm_curves.append(proj2 / v2_tr[-1])

        if len(ref_norm_curves) < 2:
            continue

        curves_arr = np.array(ref_norm_curves)   # shape (n_similar, max_ahead)
        q_curves = {q: np.percentile(curves_arr, q * 100, axis=0)
                    for q in quantiles_sorted}

        # --- Auswertung gegen tatsächliche Realwerte der Zielgemeinde ---
        last_train_val = v_tr[-1]
        for ahead in range(1, max_ahead + 1):
            idx = n_train + ahead - 1
            if idx >= n:
                break
            actual = v_hist[idx]
            if actual <= 0:
                continue
            actual_norm = actual / last_train_val

            q_dict_here = {q: float(q_curves[q][ahead - 1]) for q in quantiles_sorted}
            mape, wis = _wis_from_quantile_dict(q_dict_here, quantiles_sorted, actual_norm)
            mapes.append(mape)
            wiss.append(wis)

    mean_mape = float(np.mean(mapes)) if mapes else 999.0
    mean_wis  = float(np.mean(wiss))  if wiss  else 1e9
    return mean_mape, mean_wis


def _hindcast_single_pair(
    gemeinde: str,
    mname: str,
    det_proj: Dict,
) -> Tuple[str, str, float, float]:
    """
    Hilfsfunktion für die parallele Verarbeitung eines einzelnen
    (Gemeinde, Modell)-Paares.

    Parameter
    ----------
    gemeinde : str   Zielgemeinde
    mname    : str   Modellname
    det_proj : dict  Ergebnis aus Schritt 1 für ALLE Gemeinden

    Returns
    -------
    (gemeinde, mname, mape, wis) : Tuple[str, str, float, float]
    """
    mape, wis = hindcast_single_model(mname, gemeinde, det_proj)
    return gemeinde, mname, mape, wis


def step3_hindcasting(
    det_proj: Dict,
    target_gemeinden: List[str],
) -> Tuple[Dict, Dict]:
    """
    Schritt 3: Walk-Forward-Hindcasting und Modellgewichte,
    für explizit angegebene Zielgemeinden.

    Führt für jede Zielgemeinde × jedes der 12 Modelle ein vollständiges
    Walk-Forward-Hindcasting durch.
    Referenzgemeinden für die Ähnlichkeitssuche sind alle übrigen
    Gemeinden in `det_proj`.

    Parameter
    ----------
    det_proj          : dict   Ergebnis aus Schritt 1 für ALLE Gemeinden
                                (Zielgemeinden UND Referenzpool)
    target_gemeinden  : list   Gemeinden, für die Gewichte berechnet werden

    Returns
    -------
    weights : dict  Gemeindeschlüssel → {key: Gewicht}
    scores  : dict  Gemeindeschlüssel → {key: {'mape': float, 'wis': float}}
    """
    missing = [g for g in target_gemeinden if g not in det_proj]
    if missing:
        raise ValueError(f"Zielgemeinden nicht in det_proj gefunden: {missing}")

    print("  Walk-Forward-Hindcasting")
    if HINDCAST_MAX_SIMILAR:
        print(f"  Referenzpool: {len(det_proj) - 1} Gemeinden je Zielgemeinde "
            f"(max. {HINDCAST_MAX_SIMILAR} ähnliche werden je Split gefittet)")
    else:
        print(f"  Referenzpool: {len(det_proj) - 1} Gemeinden je Zielgemeinde ")

    tasks = [(g, m) for g in target_gemeinden for m in ALL_MODELS]
    print(f"  Schritt 3 (Parallel, Gemeinde×Modell): {len(target_gemeinden)} "
          f"Zielgemeinden × {len(ALL_MODELS)} Modelle = {len(tasks)} Aufgaben")

    executor = Parallel(n_jobs=-1, return_as="generator")
    tasks_generator = executor(delayed(_hindcast_single_pair)(g, m, det_proj) for g, m in tasks)

    results = list(tqdm(tasks_generator, total=len(tasks), desc="Hindcasting (Gemeinde × Modell)"))

    mape_by_gemeinde = {g: {} for g in target_gemeinden}
    wis_by_gemeinde = {g: {} for g in target_gemeinden}
    for g, mname, mape, wis in results:
        mape_by_gemeinde[g][mname] = mape
        wis_by_gemeinde[g][mname]  = wis

    weights = {}
    scores = {}

    for g in target_gemeinden:
        wis_d   = wis_by_gemeinde[g]
        wis_arr = np.array([wis_d[m] for m in ALL_MODELS])
        wis_arr = np.clip(wis_arr, 1e-6, None)
        inv     = 1.0 / wis_arr ** 2
        inv    /= inv.sum()

        weights[g] = {m: float(w) for m, w in zip(ALL_MODELS, inv)}
        scores[g]  = {m: {"mape": mape_by_gemeinde[g][m], "wis": wis_d[m]}
                      for m in ALL_MODELS}

    return weights, scores