"""
visualization/plots.py — Plot-Funktionen für PV-Hochlaufszenarien.

Alle Funktionen speichern direkt nach OUT_PLOTS und geben den Dateipfad zurück.

Öffentliche Funktionen:
  plot_fit_validation()   : Alle 12 Modell-Fits vs. historische Daten
  plot_hochlauf_gemeinde(): Quantilband + Szenariopfade für eine Gemeinde
  plot_hindcast_heatmap() : MAPE / WIS / Gewichte als Heatmap
  plot_national()         : Nationale Aggregation
"""

from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pv_hochlauf.core.config import BASE_DIR, OUT_PLOTS, MODEL_COLORS
from pv_hochlauf.core.models import ALL_MODELS, MODEL_FNS


# Dictionary erstellen: {Gemeindeschluessel: Gemeindename}
df_gemeinden = pd.read_pickle(BASE_DIR / "Daten" / "mastr_data.pkl")
gemeinde_dict = (
    df_gemeinden[['Gemeindeschluessel', 'Gemeinde']]
    .drop_duplicates()
    .set_index('Gemeindeschluessel')['Gemeinde']
    .to_dict()
)


def _nearest_quantile(available_qs, target):
    """
    Findet das in config.QUANTILES tatsächlich vorhandene Quantil, das
    einem Zielwert (z.B. 0.05) am nächsten liegt.
    """
    return min(available_qs, key=lambda q: abs(q - target))


def _resolve_bands(qs_dict, target_pairs=((0.05, 0.95), (0.10, 0.90), (0.25, 0.75))):
    """
    Löst die klassischen Bänder (P5-95, P10-90, P25-75) auf die
    tatsächlich in config.QUANTILES vorhandenen Werte auf.
    """
    available = sorted(qs_dict.keys())
    bands, seen = [], set()
    for lo_t, hi_t in target_pairs:
        lo = _nearest_quantile(available, lo_t)
        hi = _nearest_quantile(available, hi_t)
        if lo == hi or (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        bands.append((lo, hi))
    return bands


def _style_ax(ax, title: str, ylabel: str, xlabel: str = "Jahr") -> None:
    """Einheitliches Styling für alle Achsen."""
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _safe_filename(name: str) -> str:
    """Ersetzt Sonderzeichen für sichere Dateinamen."""
    return name.replace(" ", "_").replace("/", "-").replace("\\", "-")

def _get_name(gemeinde: str) -> str:
    """Gibt den Gemeindenamen zurück."""
    if gemeinde_dict.get(gemeinde):
        return gemeinde_dict.get(gemeinde)
    else:
        print("Kein Eintrag für diesen Gemeindeschlüssel:", gemeinde)
        return gemeinde

def plot_fit_validation(
    gemeinde: str,
    det_proj: Dict,
    filename: Optional[str] = None,
) -> Path:
    """
    2×6-Grid: Alle 12 Modell-Fits vs. historische Daten für eine Gemeinde.

    Parameter
    ----------
    gemeinde  : str   Gemeindeschlüssel
    det_proj  : dict  Ergebnis aus Schritt 1
    filename  : str   Optional: Dateiname (Standard: fit_validierung_<Gemeinde>.png)

    Returns
    -------
    Path  Pfad zur gespeicherten Abbildung
    """
    d      = det_proj[gemeinde]
    gemeinde = _get_name(gemeinde)
    t_hist = d["t_hist"]
    v_hist = d["v_hist"]
    t_proj = d["t_proj"]

    fig, axes = plt.subplots(2, 6, figsize=(22, 7))
    fig.suptitle(f"Fit-Validierung — {gemeinde}", fontsize=12, fontweight="bold")

    for ax, mname in zip(axes.flatten(), ALL_MODELS):
        md     = d["models"][mname]
        fitted = md["fitted"]
        proj   = md["proj"]

        ax.scatter(t_hist, v_hist / 1000, color="black", s=15, zorder=5,
                   label="MaStR hist.")
        ax.plot(t_hist, fitted / 1000, color=MODEL_COLORS[mname],
                linewidth=1.8, linestyle="--",
                label=f"Fit (R²={md['r2']:.3f})" if md["r2"] is not None
                      else "Fit (Ersatz)")
        # Projektion ab letztem historischen Jahr
        mask = t_proj >= t_hist[-1]
        ax.plot(t_proj[mask], proj[mask] / 1000,
                color=MODEL_COLORS[mname], linewidth=1.4, alpha=0.75)
        ax.axvline(t_hist[-1], color="gray", linestyle=":", linewidth=0.8)
        _style_ax(ax, mname, "MWp kumuliert")
        ax.legend(fontsize=6)

    plt.tight_layout()
    fname = filename or f"fit_validierung_{_safe_filename(gemeinde)}.png"
    path  = OUT_PLOTS / fname
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


def plot_hochlauf_gemeinde(
    gemeinde: str,
    ensemble: Dict,
    C_hi: Optional[float] = None,
    filename: Optional[str] = None,
) -> Path:
    """
    2-Panel: Quantilband (links) + konkrete Szenariopfade (rechts).

    Parameter
    ----------
    gemeinde  : str            Gemeindeschlüssel
    ensemble  : dict           Ergebnis aus Schritt 4
    C_hi      : float | None   Sättigungsobergrenze
    filename  : str            Optional: Dateiname

    Returns
    -------
    Path  Pfad zur gespeicherten Abbildung
    """
    d      = ensemble[gemeinde]
    gemeinde = _get_name(gemeinde)
    t_proj = d["t_proj"].astype(int)
    qs     = d["quantiles"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    if C_hi is not None:
        title = f"PV-Hochlauf — {gemeinde} (C_hi = {C_hi/1000:.2f} MWp)"
    else:
        title = f"PV-Hochlauf — {gemeinde} (Ersatzprojektion)"
    fig.suptitle(title, fontsize=12, fontweight="bold")

    # --- Panel links: Quantilband ---
    bands = _resolve_bands(qs)
    alphas = [0.12, 0.18, 0.28]
    for (lo, hi), a in zip(bands, alphas):
        ax1.fill_between(t_proj, qs[lo] / 1000, qs[hi] / 1000,
                         alpha=a, color="#2171b5",
                         label=f"P{int(lo*100)}–P{int(hi*100)}")
    ax1.plot(t_proj, qs[0.50] / 1000, color="#2171b5",
             linewidth=2.5, label="Median (P50)")
    _style_ax(ax1, "Probabilistisches Quantilband", "MWp kumuliert")
    ax1.legend(fontsize=8, framealpha=0.85)

    # --- Panel rechts: Szenariopfade ---
    q_lo10 = _nearest_quantile(sorted(qs.keys()), 0.10)
    q_hi90 = _nearest_quantile(sorted(qs.keys()), 0.90)
    for path in d["paths"]:
        ax2.plot(t_proj, path / 1000, alpha=0.20, linewidth=0.7, color="#6baed6")
    ax2.plot(t_proj, qs[0.50] / 1000, color="#084594",
             linewidth=2.5, zorder=5, label="Median")
    ax2.plot(t_proj, qs[q_lo10] / 1000, color="#6baed6",
             linewidth=1.5, linestyle="--", label=f"P{int(q_lo10*100)}")
    ax2.plot(t_proj, qs[q_hi90] / 1000, color="#084594",
             linewidth=1.5, linestyle="--", label=f"P{int(q_hi90*100)}")
    n_paths = d["paths"].shape[0]
    _style_ax(ax2, f"Konkrete Szenariopfade (N={n_paths})", "MWp kumuliert")
    ax2.legend(fontsize=8, framealpha=0.85)

    plt.tight_layout()
    fname = filename or f"hochlauf_{_safe_filename(gemeinde)}.png"
    path  = OUT_PLOTS / fname
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


def plot_hindcast_heatmap(
    scores: Dict,
    weights: Dict,
    gemeinde: str,
    filename: Optional[str] = None,
) -> Path:
    """
    1×3-Heatmap: MAPE / WIS / Gewicht für alle 12 Modelle einer Gemeinde.

    Parameter
    ----------
    scores    : dict  {mname: {'mape': float, 'wis': float}}
    weights   : dict  {mname: float}
    gemeinde  : str   Gemeindeschlüssel
    filename  : str   Optional: Dateiname

    Returns
    -------
    Path  Pfad zur gespeicherten Abbildung
    """
    gemeinde = _get_name(gemeinde)
    fig, axes = plt.subplots(1, 3, figsize=(16, 3.5))
    fig.suptitle(f"Hindcasting-Performance — {gemeinde}",
                 fontsize=11, fontweight="bold")

    metrics = [
        ({m: scores[m]["mape"] for m in ALL_MODELS}, "MAPE (%)",  "RdYlGn_r"),
        ({m: scores[m]["wis"]  for m in ALL_MODELS}, "WIS",       "RdYlGn_r"),
        (weights,                                     "Gewicht",   "YlGn"),
    ]

    for ax, (vals_d, title, cmap) in zip(axes, metrics):
        vals = np.array([vals_d[m] for m in ALL_MODELS]).reshape(1, -1)
        im   = ax.imshow(vals, aspect="auto", cmap=cmap,
                         vmin=vals.min(), vmax=vals.max())
        ax.set_xticks(range(len(ALL_MODELS)))
        ax.set_xticklabels(ALL_MODELS, rotation=40, ha="right", fontsize=7)
        ax.set_yticks([])
        ax.set_title(title, fontsize=9, fontweight="bold")
        fmt = ".3f" if title == "Gewicht" else ".1f"
        for j, m in enumerate(ALL_MODELS):
            ax.text(j, 0, f"{vals_d[m]:{fmt}}", ha="center",
                    va="center", fontsize=7)
        plt.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    fname = filename or f"hindcast_{_safe_filename(gemeinde)}.png"
    path  = OUT_PLOTS / fname
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


def plot_national(
    nat_q: Dict,
    nat_paths: np.ndarray,
    years: np.ndarray,
    filename: Optional[str] = None,
) -> Path:
    """
    2-Panel: Nationales Quantilband (links) + Szenariopfade (rechts).

    Parameter
    ----------
    nat_q     : dict         q → pd.Series [kW]
    nat_paths : np.ndarray   (n_paths × n_jahre) [kW]
    years     : np.ndarray   Jahresarray
    filename  : str          Optional: Dateiname

    Returns
    -------
    Path  Pfad zur gespeicherten Abbildung
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("PV-Hochlauf — Nationale Aggregation (alle Gemeinden)",
                 fontsize=12, fontweight="bold")

    # Umrechnung kW → GW
    gw = {q: nat_q[q].values / 1e6 for q in nat_q}

    bands = _resolve_bands(gw)
    alphas = [0.12, 0.18, 0.28]
    for (lo, hi), a in zip(bands, alphas):
        ax1.fill_between(years, gw[lo], gw[hi], alpha=a, color="#2171b5",
                         label=f"P{int(lo*100)}–P{int(hi*100)}")
    ax1.plot(years, gw[0.50], color="#2171b5", linewidth=2.5, label="Median (P50)")
    _style_ax(ax1, "Quantilband", "GW kumuliert")
    ax1.legend(fontsize=8, framealpha=0.85)

    q_lo10 = _nearest_quantile(sorted(gw.keys()), 0.10)
    q_hi90 = _nearest_quantile(sorted(gw.keys()), 0.90)
    for path_kw in nat_paths:
        ax2.plot(years, path_kw / 1e6, alpha=0.12, linewidth=0.6, color="#6baed6")
    ax2.plot(years, gw[0.50], color="#084594", linewidth=2.5,
             zorder=5, label="Median")
    ax2.plot(years, gw[q_lo10], color="#6baed6", linewidth=1.5,
             linestyle="--", label=f"P{int(q_lo10*100)}")
    ax2.plot(years, gw[q_hi90], color="#084594", linewidth=1.5,
             linestyle="--", label=f"P{int(q_hi90*100)}")
    n_paths = nat_paths.shape[0]
    _style_ax(ax2, f"Szenariopfade (N={n_paths})", "GW kumuliert")
    ax2.legend(fontsize=8, framealpha=0.85)

    plt.tight_layout()
    fname = filename or "hochlauf_national.png"
    path  = OUT_PLOTS / fname
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path
