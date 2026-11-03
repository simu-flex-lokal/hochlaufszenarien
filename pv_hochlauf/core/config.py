"""
config.py — Zentrale Konfiguration für den PV-Hochlauf.

Alle Parameter die das Verhalten der Pipeline steuern sind hier gebündelt.
Für Produktivläufe TEST_MODE = False setzen.
"""

import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Ausgabeverzeichnisse
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[3]
# Phase-1-Anpassung (Integration): Laufzeit-Artefakte nach data/ (gitignored),
# damit der Repo-Root sauber bleibt. Original: BASE_DIR/outputs bzw. /cache_daten.
_RT        = BASE_DIR / "data" / "pv_hochlauf"
OUT_ROOT   = _RT / "outputs"
OUT_PLOTS  = OUT_ROOT / "plots"
OUT_CSV    = OUT_ROOT / "csv"
OUT_PICKLE = _RT / "cache"

for _d in [OUT_PLOTS, OUT_CSV, OUT_PICKLE]:
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Test-Modus
# ---------------------------------------------------------------------------
# TEST_MODE = True  → schneller Entwicklungslauf mit reduzierten Parametern
# TEST_MODE = False → vollständiger Produktivlauf
TEST_MODE = False

TEST_MAX_GEMEINDEN = None  # None = alle; int = Top-N nach Leistung
TEST_MAX_AHEAD     = 10     # Hindcasting-Horizont (Produktiv: 10)
TEST_DE_MAXITER    = 100    # DE-Iterationen    (Produktiv: 200)
TEST_DE_POPSIZE    = 8     # DE-Populationsgröße (Produktiv: 8)
TEST_N_PATHS       = 30    # Szenariopfade      (Produktiv: 50)

# ---------------------------------------------------------------------------
# Produktiv-Parameter (automatisch je nach TEST_MODE gesetzt)
# ---------------------------------------------------------------------------
PROJ_END         = 2050
MIN_TRAIN_YRS    = 8      # Mindest-Trainingsjahre für Hindcasting
SIMILARITY_PCT   = 30     # Perzentil der euklid. Distanz für ähnliche Gemeinden
YEAR_MIN         = 1995
YEAR_MAX         = 2025   # 2026 ist noch nicht vollständig und würde den Fit verfälschen

MAX_AHEAD_YRS    = TEST_MAX_AHEAD  if TEST_MODE else 10
N_SCENARIO_PATHS = TEST_N_PATHS    if TEST_MODE else 50
DE_MAXITER       = TEST_DE_MAXITER if TEST_MODE else 200
DE_POPSIZE       = TEST_DE_POPSIZE if TEST_MODE else 8

# Obergrenze für die Anzahl der pro Split zu fittenden Referenzgemeinden beim Hindcasting
HINDCAST_MAX_SIMILAR = 150

# Cache-Verhalten: False = Cache nutzen wenn vorhanden; True = immer neu rechnen
FORCE_RECOMPUTE  = False
# Bei neuer Berechnung: SAVE_DET_PROJ = True → deterministische Projektionen werden im Daten-Cache gespeichert
SAVE_DET_PROJ = False

# ---------------------------------------------------------------------------
# Vorfilterung auf Wohngebäude (optional)
# ---------------------------------------------------------------------------
# FILTER_RESIDENTIAL = True  → nur Wohngebäude-PV berücksichtigen
# FILTER_RESIDENTIAL = False → alle Anlagen (kein Filter)
FILTER_RESIDENTIAL = True
 
# Maximale Anlagengröße [kWp] für Wohngebäude-PV (Filter).
MAX_KWP_RESIDENTIAL = 100.0
 
# Nutzungsbereiche die als Wohngebäude gelten.
# Mögliche Werte im MaStR:
#   'Haushalt', 'Landwirtschaft', 'Gewerbe, Handel und Dienstleistungen',
#   None, 'Sonstige', 'Industrie', 'Öffentliches Gebäude'
RESIDENTIAL_NUTZUNG = ["Haushalt"]
 
# True  → Anlagen ohne Nutzungsbereich (None) werden eingeschlossen
INCLUDE_NONE_NUTZUNG = True

# Sättigungspotenzial via ETHOS.BUILDA berechnen
# True  → fetch_builda_saturation_bulk() wird aufgerufen (builda_client erforderlich)
# False → Fallback: C_hi = letzter Bestand × default_multiplier
USE_BUILDA_SATURATION = True

# ---------------------------------------------------------------------------
# zu berechnende Quantile
# ---------------------------------------------------------------------------
# Entspricht 99 Quantilen wie in Zielonka et al.
# QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95] # vereinfacht auf 7 Quantile
QUANTILES = [i / 20 for i in range(1, 20)]  # 19 Quantile

# ---------------------------------------------------------------------------
# Zielgemeinden (optional)
# ---------------------------------------------------------------------------
# None    → alle Gemeinden vollständig verarbeiten
# Liste   → Schritt 1 für ALLE (Referenzpool), Schritte 2–4 nur für diese
# Beispiel für Kreuzau, Jülich und München (anhand des AGS): TARGET_GEMEINDEN = ["05358028", "05358024", "09162000"]
TARGET_GEMEINDEN = ["05358028", "05358024", "09162000"]
# TARGET_GEMEINDEN = None

# ---------------------------------------------------------------------------
# Visualisierung
# ---------------------------------------------------------------------------
MODEL_COLORS = {
    "Bass":           "#e41a1c",
    "Bertalanffy":    "#377eb8",
    "Gompertz":       "#4daf4a",
    "Logistisch":     "#984ea3",
    "Richards-4p":    "#ff7f00",
    "Richards-5p":    "#a65628",
    "Bi-Bass":        "#fb9a99",
    "Bi-Bertalanffy": "#a6cee3",
    "Bi-Gompertz":    "#b2df8a",
    "Bi-Logistisch":  "#cab2d6",
    "Bi-Richards-4p": "#fdbf6f",
    "Bi-Richards-5p": "#d2b48c",
}
