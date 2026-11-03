"""
pipeline/probabilistic.py — Schritt 2: Probabilistische Projektionen.

Erzeugt für jede Zielgemeinde und jedes Modell ein Wahrscheinlichkeitsband,
indem Projektionen ähnlicher Gemeinden aggregiert werden (nach Zielonka et al.).

Öffentliche Funktionen:
  normalize_ts()              : Normiert Zeitreihe auf letzten Wert
  euclidean_dist()            : Euklidische Distanz zweier Zeitreihen
  step2_probabilistic()       : Schritt 2 für alle Zielgemeinden (parallel)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from joblib import Parallel, delayed
from tqdm import tqdm

from pv_hochlauf.core.config import QUANTILES, SIMILARITY_PCT, PROJ_END
from pv_hochlauf.core.models import ALL_MODELS


def normalize_ts(v: np.ndarray) -> np.ndarray:
    """
    Normiert eine Zeitreihe auf ihren letzten Wert (= 1.0 im letzten Jahr).

    Ziel: Nur die Form (Wachstumsdynamik) vergleichen, nicht die absolute Höhe.
    Notwendig damit kleine und große Gemeinden verglichen werden können.

    Parameter
    ----------
    v : np.ndarray  kumulierte Zeitreihe

    Returns
    -------
    np.ndarray  normierte Zeitreihe (letzter Wert = 1.0)
    """
    last = float(v[-1])
    return v / last if last > 0 else np.zeros_like(v)


def euclidean_dist(a: np.ndarray, b: np.ndarray) -> float:
    """
    Euklidische Distanz zweier normierter Zeitreihen.
    Verwendet die kürzere der beiden Reihen als gemeinsame Länge.

    Parameter
    ----------
    a, b : np.ndarray  normierte historische Zeitreihen

    Returns
    -------
    float  euklidische Distanz
    """
    n = min(len(a), len(b))
    return float(np.linalg.norm(a[-n:] - b[-n:]))


def _prob_proj_single(
    target: str,
    gemeinden: List[str],
    norm_hist: Dict[str, np.ndarray],
    det_proj: Dict,
    similarity_pct: float,
    quantiles: List[float],
) -> Tuple[str, Dict]:
    """
    Erzeugt probabilistische Projektion für eine einzelne Zielgemeinde.

    Methodik nach Zielonka et al. (Schritt 2):
      1. Normierte historische Zeitreihe der Zielgemeinde berechnen
      2. Euklidische Distanz zu allen anderen Gemeinden
      3. Ähnliche Gemeinden: Distanz < similarity_pct-Perzentil
      4. Normierte Projektionskurven ähnlicher Gemeinden je Modell sammeln
      5. Quantile dieser Kurven = probabilistisches Band

    Die Variation zwischen ähnlichen Gemeinden ist die Quelle der Unsicherheit
    (empirisch begründet, keine statistischen Verteilungsannahmen).

    Parameter
    ----------
    target         : str    Zielgemeindename
    gemeinden      : list   Alle Gemeinden im Referenzpool (valide + ausgeschlossene)
    norm_hist      : dict   Normierte historische Zeitreihen aller Gemeinden
    det_proj       : dict   Deterministische Projektionen aller Gemeinden (Schritt 1)
    similarity_pct : float  Perzentil für Ähnlichkeitsschwellenwert (Standard: 30)
    quantiles      : list   Zu berechnende Quantile

    Returns
    -------
    (target, prob_proj_eintrag) : Tuple
    """
    d_target  = det_proj[target]
    nh_target = norm_hist[target]
    last_val  = float(d_target["v_hist"][-1])
    t_proj    = d_target["t_proj"]
    n_proj    = len(t_proj)

    # Distanzen zu allen anderen Gemeinden im Referenzpool
    dists = np.array([
        0.0 if g == target else euclidean_dist(nh_target, norm_hist[g])
        for g in gemeinden
    ])

    # Schwellenwert: similarity_pct-Perzentil der Nicht-Null-Distanzen
    nonzero = dists[dists > 0]
    threshold = np.percentile(nonzero, similarity_pct) if len(nonzero) > 0 else 0.0
    similar   = [gemeinden[i] for i, d in enumerate(dists) if d <= threshold]

    # Fallback: mindestens 3 ähnliche Gemeinden
    if len(similar) < 3:
        similar = [gemeinden[i] for i in np.argsort(dists)[:3]]

    # Für jedes Modell: normierte Projektionskurven ähnlicher Gemeinden sammeln
    model_quantiles: Dict[str, Dict] = {}
    for mname in ALL_MODELS:
        curves = []
        for sim in similar:
            sim_last = float(det_proj[sim]["v_hist"][-1])
            if sim_last <= 0:
                continue
            # Normierung: Projektion / letzter Wert → relativer Wachstumspfad
            proj_norm = det_proj[sim]["models"][mname]["proj"] / sim_last
            t_sim = det_proj[sim]["t_proj"]
            # Auf gemeinsame Zeitachse interpolieren falls nötig
            if len(t_sim) != n_proj or not np.allclose(t_sim, t_proj):
                proj_norm = np.interp(t_proj, t_sim, proj_norm,
                                      left=proj_norm[0], right=proj_norm[-1])
            curves.append(proj_norm)

        if len(curves) < 2:
            # Zu wenig ähnliche Kurven: eigene normierte Kurve als Fallback
            own = d_target["models"][mname]["proj"] / max(last_val, 1e-3)
            curves = [own, own]  # doppelt damit Quantile berechnet werden können

        arr   = np.array(curves)
        model_quantiles[mname] = {
            q: np.percentile(arr, q * 100, axis=0) for q in quantiles
        }

    return target, {
        "t_proj":    t_proj,
        "t_hist":    d_target["t_hist"],
        "v_hist":    d_target["v_hist"],
        "last_val":  last_val,
        "n_similar": len(similar),
        "models":    model_quantiles,
    }


def step2_probabilistic(
    det_proj: Dict,
    quantiles: List[float] = QUANTILES,
    similarity_pct: float  = SIMILARITY_PCT,
    target_gemeinden: Optional[List[str]] = None,
) -> Dict:
    """
    Schritt 2 nach Zielonka et al.: Probabilistische Projektionen je Modell.

    Alle Gemeinden in det_proj dienen als Referenzpool. Quantile werden nur 
    für Zielgemeinden berechnet.

    Parameter
    ----------
    det_proj          : dict   Ergebnis aus Schritt 1 (ALLE Gemeinden)
    quantiles         : list   Zu berechnende Quantile
    similarity_pct    : float  Ähnlichkeitsschwellenwert (Perzentil)
    target_gemeinden  : list   Optional: nur für diese Gemeinden berechnen;
                               alle anderen bleiben im Referenzpool

    Returns
    -------
    prob_proj : dict
        Gemeindename → {
          't_proj'   : np.ndarray
          't_hist'   : np.ndarray
          'v_hist'   : np.ndarray
          'last_val' : float
          'n_similar': int
          'models'   : dict  mname → {q: np.ndarray (normiert)}
        }
    """
    # Normierte historische Zeitreihen für ALLE Gemeinden (Referenzpool)
    norm_hist = {g: normalize_ts(d["v_hist"]) for g, d in det_proj.items()}
    gemeinden = list(det_proj.keys())

    # Zielgemeinden: nur für diese werden Quantile berechnet
    if target_gemeinden is not None:
        missing = [g for g in target_gemeinden if g not in det_proj]
        if missing:
            raise ValueError(
                f"Zielgemeinden nicht in det_proj: {missing}\n"
                f"Bitte Schreibweise prüfen oder TARGET_GEMEINDEN anpassen."
            )
        targets = target_gemeinden
        print(f"  Schritt 2 (Parallel): {len(targets)} Zielgemeinden "
              f"| Referenzpool: {len(gemeinden)} Gemeinden")
    else:
        targets = gemeinden
        print(f"  Schritt 2 (Parallel): {len(targets)} Gemeinden")

    results = Parallel(n_jobs=-1)(
        delayed(_prob_proj_single)(
            g, gemeinden, norm_hist, det_proj, similarity_pct, quantiles
        )
        for g in tqdm(targets, desc="Probabilistische Projektionen abgeschlossen")
    )
    return dict(results)
