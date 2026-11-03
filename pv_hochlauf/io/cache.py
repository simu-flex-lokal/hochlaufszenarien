"""
io/cache.py — Cache-System für Zwischenergebnisse.

Speichert und lädt det_proj (Schritt-1-Ergebnis) als Pickle-Datei,
um Schritt 1 bei wiederholten Läufen zu überspringen.
"""

import pickle
from pathlib import Path
from typing import Optional, Dict

from pv_hochlauf.core.config import OUT_PICKLE


def save_det_proj(det_proj: Dict, filename: str = "det_proj.pkl") -> None:
    """
    Speichert det_proj als Pickle-Datei.

    Parameter
    ----------
    det_proj : dict   Ergebnis aus step1_deterministic_parallel()
    filename : str    Dateiname im OUT_PICKLE-Verzeichnis
    """
    path = OUT_PICKLE / filename
    with open(path, "wb") as f:
        pickle.dump(det_proj, f)
    print(f"  Cache gespeichert: {path} ({len(det_proj):,} Gemeinden)")


def load_det_proj(filename: str = "det_proj.pkl") -> Optional[Dict]:
    """
    Lädt det_proj aus dem Pickle-Cache.

    Gibt None zurück wenn:
      - Datei nicht vorhanden
      - Datei nicht lesbar (korrupt)

    Parameter
    ----------
    filename : str  Dateiname im OUT_PICKLE-Verzeichnis

    Returns
    -------
    dict oder None (Cache-Miss)
    """
    path = OUT_PICKLE / filename
    if not path.exists():
        print(f"  Kein Cache vorhanden ({path}) → Schritt 1 wird neu berechnet.")
        return None

    try:
        with open(path, "rb") as f:
            det_proj = pickle.load(f)
        print(f"  Cache geladen: {path} ({len(det_proj):,} Gemeinden)")
        return det_proj
    except Exception as e:
        print(f"  Cache nicht lesbar ({e}) → Schritt 1 wird neu berechnet.")
        return None


def save_prob_proj(prob_proj: Dict, filename: str = "prob_proj.pkl") -> None:
    """
    Speichert probabilistische Projektionen (Schritt 2) gemeindeweise.
    Neue Gemeinden werden zu bestehenden Einträgen hinzugefügt.
    """
    existing = load_prob_proj(filename) or {}
    existing.update(prob_proj)
    path = OUT_PICKLE / filename
    with open(path, "wb") as f:
        pickle.dump(existing, f)
    print(f"  prob_proj gespeichert: {len(existing)} Gemeinden → {path}")


def load_prob_proj(filename: str = "prob_proj.pkl") -> Optional[Dict]:
    """
    Lädt probabilistische Projektionen aus Cache.
    Gibt dict oder None zurück.
    """
    return load_pickle(filename)


def save_weights_scores(weights: Dict, scores: Dict, filename: str = "weights_scores.pkl") -> None:
    """
    Speichert Hindcasting-Gewichte und -Scores (Schritt 3) gemeindeweise.
    Neue Gemeinden werden zu bestehenden Einträgen hinzugefügt.
    """
    existing = load_weights_scores(filename) or {"weights": {}, "scores": {}}
    existing["weights"].update(weights)
    existing["scores"].update(scores)
    path = OUT_PICKLE / filename
    with open(path, "wb") as f:
        pickle.dump(existing, f)
    print(f"  weights/scores gespeichert: {len(existing['weights'])} Gemeinden → {path}")


def load_weights_scores(filename: str = "weights_scores.pkl") -> Optional[Dict]:
    """
    Lädt Hindcasting-Gewichte und Scores aus Cache.
    Gibt dict mit Keys 'weights' und 'scores' oder None zurück.
    """
    return load_pickle(filename)


def save_pickle(obj, filename: str) -> None:
    """
    Speichert ein beliebiges Objekt als Pickle (für Zwischenergebnisse).

    Parameter
    ----------
    obj      : beliebiges Python-Objekt
    filename : str  Dateiname im OUT_PICKLE-Verzeichnis
    """
    path = OUT_PICKLE / filename
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"  Gespeichert: {path}")


def load_pickle(filename: str):
    """
    Lädt ein beliebiges Pickle-Objekt.

    Parameter
    ----------
    filename : str  Dateiname im OUT_PICKLE-Verzeichnis

    Returns
    -------
    Objekt oder None bei Fehler
    """
    path = OUT_PICKLE / filename
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  Konnte {path} nicht laden: {e}")
        return None
