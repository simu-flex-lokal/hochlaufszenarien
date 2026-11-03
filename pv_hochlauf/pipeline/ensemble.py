"""
pipeline/ensemble.py — Schritt 4: Gewichtetes Ensemble + Ersatzprojektionen.

Kombiniert die 12 Modell-Projektionen gewichtet zur finalen Projektion.
Ausgeschlossene Gemeinden erhalten Ersatzprojektionen auf Basis der
durchschnittlichen Wachstumsrate nicht-ausgeschlossener Gemeinden
(exakt nach Zielonka et al. Supplementary A.5 / Tabelle S1e).

Öffentliche Funktionen:
  step4_ensemble()          : Schritt 4 für valide Zielgemeinden
  compute_excluded_ensemble(): Ersatzprojektionen für ausgeschlossene Gemeinden
  aggregate_national()      : Nationale Aggregation (Quantile summieren)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from pv_hochlauf.core.config import QUANTILES, N_SCENARIO_PATHS, PROJ_END
from pv_hochlauf.core.models import ALL_MODELS


def _ensemble_single(
    gemeinde: str,
    pp: Dict,
    w_dict: Dict[str, float],
    quantiles: List[float],
    n_paths: int,
) -> Tuple[str, Dict]:
    """
    Berechnet das gewichtete Ensemble für eine einzelne Gemeinde.

    Gewichtete Quantile (Vincentization, nach Zielonka et al. Tab. S1e):
      q_ensemble(t) = Σ_m w_m × q_m(t)   [normiert]
      → × last_val  [absolute kW]

    Szenariopfade:
      Werden direkt aus der bereits kombinierten Quantilfunktion
      q_ensemble abgeleitet.
      Für jeden Pfad i:
        (a) Quantil q ∈ [0.05, 0.95] gleichmäßig ziehen
        (b) q_ensemble bei diesem Quantilniveau interpolieren
            (zwischen den nächstgelegenen berechneten Quantilen)

    Parameter
    ----------
    gemeinde  : str    Gemeindename (für reproduzierbaren Seed)
    pp        : dict   Prob. Projektion aus Schritt 2 (normierte Quantile)
    w_dict    : dict   Modellgewichte aus Schritt 3
    quantiles : list   Zu berechnende Quantile
    n_paths   : int    Anzahl Szenariopfade

    Returns
    -------
    (gemeinde, ensemble_eintrag) : Tuple
    """
    last_val = pp["last_val"]
    t_proj   = pp["t_proj"]
    n_proj   = len(t_proj)
    w_arr    = np.array([w_dict[m] for m in ALL_MODELS])

    # Gewichtete Quantile — unverändert, wie bisher (= Vincentization)
    ens_q = {}
    for q in quantiles:
        weighted = sum(w_arr[i] * pp["models"][m][q]
                       for i, m in enumerate(ALL_MODELS))
        ens_q[q] = np.maximum.accumulate(weighted * last_val)

    rng    = np.random.default_rng(abs(hash(gemeinde)) % (2**32))
    q_vals = sorted(quantiles)
    paths  = np.zeros((n_paths, n_proj))

    for i in range(n_paths):
        q_rand = float(rng.uniform(0.05, 0.95))
        q_lo   = max([qv for qv in q_vals if qv <= q_rand], default=q_vals[0])
        q_hi   = min([qv for qv in q_vals if qv >= q_rand], default=q_vals[-1])
        if q_lo == q_hi:
            curve = ens_q[q_lo]
        else:
            a     = (q_rand - q_lo) / (q_hi - q_lo)
            curve = (1 - a) * ens_q[q_lo] + a * ens_q[q_hi]
        paths[i] = curve   # bereits absolute kW, da ens_q schon skaliert ist

    return gemeinde, {
                "t_proj": t_proj,
                "quantiles": ens_q,
                "paths": paths, 
                "last_val": last_val
            }


def step4_ensemble(
    prob_proj: Dict,
    weights: Dict,
    quantiles: List[float] = QUANTILES,
    n_paths: int           = N_SCENARIO_PATHS,
) -> Dict:
    """
    Schritt 4 nach Zielonka et al.: Gewichtetes Ensemble für valide Zielgemeinden.

    Kombiniert die 12 Modell-Quantilkurven (Schritt 2) mit den Hindcast-Gewichten
    (Schritt 3) zur finalen probabilistischen Projektion.

    Parameter
    ----------
    prob_proj : dict   Ergebnis aus Schritt 2 (nur Zielgemeinden)
    weights   : dict   Ergebnis aus Schritt 3 (Hindcast-Gewichte)
    quantiles : list   Zu berechnende Quantile
    n_paths   : int    Anzahl konkreter Szenariopfade

    Returns
    -------
    ensemble : dict
        Gemeindename → {
          't_proj'    : np.ndarray
          'quantiles' : dict  q → np.ndarray [kW]
          'paths'     : np.ndarray  (n_paths × n_proj_jahre) [kW]
          'last_val'  : float
        }
    """
    print(f"  Schritt 4 (Parallel): {len(prob_proj)} Gemeinden × {n_paths} Pfade")

    results = Parallel(n_jobs=-1)(
        delayed(_ensemble_single)(
            g, pp,
            weights.get(g, {m: 1 / len(ALL_MODELS) for m in ALL_MODELS}),
            quantiles, n_paths,
        )
        for g, pp in prob_proj.items()
    )
    return dict(results)


def compute_excluded_ensemble(
    gemeinde_ts_excl: Dict,
    prob_proj_valid: Dict,
    weights_valid: Dict,
    quantiles: List[float] = QUANTILES,
    n_paths: int           = N_SCENARIO_PATHS,
) -> Dict:
    """
    Schritt 4 (Ergänzung) nach Zielonka et al. Supplementary A.5 / Tabelle S1e:
    Ersatzprojektionen für ausgeschlossene Gemeinden.

    Methodik (exakt nach Paper):
      1. Durchschnittliche Modellgewichte über alle validen Gemeinden berechnen
      2. Quantile aller validen Gemeinden (aus prob_proj_valid) kombinieren →
         mittlerer normierter Wachstumspfad
      3. Für jede ausgeschlossene Gemeinde:
           proj(t) = mean_norm(t) × last_val
         Falls last_val = 0: Dummy-Multiplikation dann Dummy subtrahieren.

    Parameter
    ----------
    gemeinde_ts_excl : dict   Ausgeschlossene Gemeinden (Zeitreihen)
    prob_proj_valid  : dict   Probabilistische Projektionen valider Gemeinden
    weights_valid    : dict   Hindcast-Gewichte valider Gemeinden
    quantiles        : list   Zu berechnende Quantile
    n_paths          : int    Anzahl Szenariopfade

    Returns
    -------
    ensemble_excl : dict  (gleiche Struktur wie step4_ensemble-Output)
    """
    if not gemeinde_ts_excl or not prob_proj_valid:
        return {}

    # Gemeinsame Zeitachse aus validen Gemeinden
    t_proj_ref = next(iter(prob_proj_valid.values()))["t_proj"]
    n_proj     = len(t_proj_ref)

    # Schritt 1: Durchschnittliche Modellgewichte aller validen Gemeinden
    avg_weights: Dict[str, float] = {}
    for mname in ALL_MODELS:
        vals = [weights_valid[g][mname] for g in weights_valid if mname in weights_valid[g]]
        avg_weights[mname] = float(np.mean(vals)) if vals else 1.0 / len(ALL_MODELS)

    # Normieren: Summe = 1
    total = sum(avg_weights.values())
    avg_weights = {m: w / total for m, w in avg_weights.items()}
    w_arr = np.array([avg_weights[m] for m in ALL_MODELS])

    # Schritt 2: Mittlere normierte Quantilkurven über alle validen Gemeinden.
    # Problem: verschiedene Gemeinden können unterschiedlich lange t_proj haben
    # → alle Kurven auf gemeinsame Referenzzeitachse interpolieren
    mean_norm_q: Dict[float, np.ndarray] = {}
    for q in quantiles:
        curves = []
        for g, pp in prob_proj_valid.items():
            # Gewichtete Summe über Modelle → eine Kurve pro valider Gemeinde
            weighted = sum(w_arr[i] * pp["models"][m][q]
                           for i, m in enumerate(ALL_MODELS))
            # Auf Referenzzeitachse interpolieren (behebt inhomogene Längen)
            t_g = pp["t_proj"]
            if len(weighted) != n_proj or not np.allclose(t_g, t_proj_ref):
                weighted = np.interp(t_proj_ref, t_g, weighted,
                                     left=weighted[0], right=weighted[-1])
            curves.append(np.asarray(weighted))
        mean_norm_q[q] = np.maximum.accumulate(np.mean(np.array(curves), axis=0))

    # Dummy-Wert: Median der Erstinstallationen valider Gemeinden
    # (für Gemeinden mit last_val = 0)
    first_vals = []
    for pp in prob_proj_valid.values():
        v  = pp["v_hist"]
        nz = v[v > 0]
        if len(nz) > 0:
            first_vals.append(nz[0])
    dummy_val = float(np.median(first_vals)) if first_vals else 1.0

    # Schritt 3: Skalierung auf jede ausgeschlossene Gemeinde
    ensemble_excl: Dict[str, Dict] = {}
    q_vals        = sorted(quantiles)
    model_probs   = w_arr / w_arr.sum()

    for gemeinde, ts in gemeinde_ts_excl.items():
        v_hist    = ts["kW_kum"].values.astype(float)
        last_val  = float(v_hist[-1])
        use_dummy = (last_val == 0)
        scale     = dummy_val if use_dummy else last_val

        ens_q: Dict[float, np.ndarray] = {}
        for q in quantiles:
            scaled = mean_norm_q[q] * scale
            if use_dummy:
                # Dummy wieder abziehen: Projektion startet bei 0
                scaled = np.maximum(scaled - dummy_val, 0)
            ens_q[q] = np.maximum.accumulate(scaled)

        # Szenariopfade
        rng   = np.random.default_rng(abs(hash(gemeinde)) % (2 ** 32))
        paths = np.zeros((n_paths, n_proj))
        for i in range(n_paths):
            q_rand = float(rng.uniform(0.05, 0.95))
            q_lo   = max([qv for qv in q_vals if qv <= q_rand], default=q_vals[0])
            q_hi   = min([qv for qv in q_vals if qv >= q_rand], default=q_vals[-1])
            if q_lo == q_hi:
                curve = ens_q[q_lo]
            else:
                a     = (q_rand - q_lo) / (q_hi - q_lo)
                curve = (1 - a) * ens_q[q_lo] + a * ens_q[q_hi]
            paths[i] = np.maximum.accumulate(curve)

        ensemble_excl[gemeinde] = {
            "t_proj":    t_proj_ref,
            "quantiles": ens_q,
            "paths":     paths,
            "last_val":  last_val,
        }

    print(f"  Ersatzprojektionen: {len(ensemble_excl)} ausgeschlossene Gemeinden "
          f"(Ø Gewichte aus {len(weights_valid)} validen Gemeinden)")
    return ensemble_excl