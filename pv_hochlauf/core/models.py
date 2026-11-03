"""
models.py — S-Kurven-Modelle nach Zielonka et al. (2023).

Enthält:
  - 6 uniforme S-Kurven: Bass, Bertalanffy, Gompertz, Logistisch,
    Richards-4p, Richards-5p
  - 6 Bi-S-Kurven (lineare Superposition zweier Phasen)
  - Modell-Registry: ALL_MODELS, MODEL_FNS
  - Parameter-Bounds nach Supplementary A.6
"""

import numpy as np

# =============================================================================
# UNIFORME S-KURVEN
# Alle Modelle haben die Signatur f(t, *params) mit:
#   t  : Jahreszahl (absolut, z.B. 2005.0)
#   C  : Sättigungsniveau (obere Grenze)
#   z  : vertikaler Shift (Startniveau, ≥ 0)
#   t0 : Wendepunkt-Jahr (freier Parameter, nach Supp. A.6)
# =============================================================================

def bass(t, p, q, C, z, t0):
    """
    Bass-Diffusionsmodell.
    
    Quelle:
    Bass, F. M. (1969). "A New Product Growth for Model Consumer Durables"

    Parameter
    ----------
    p  : Innovationskoeffizient (externe Einflüsse, z.B. Förderung)
    q  : Imitationskoeffizient  (Peer-Effekte, soziale Diffusion)
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Referenzjahr (Wendepunkt)
    """
    tau = np.asarray(t, float) - t0
    exp = np.exp(-(p + q) * tau)
    return np.clip(z + (C - z) * (1 - exp) / (1 + (q / p) * exp), z, C)


def bertalanffy(t, b, k, C, z, t0):
    """
    Von-Bertalanffy-Wachstumsmodell.
    
    Quelle:
    von Bertalanffy, L. (1938). "A quantitative theory of organic growth (Inquiries on growth laws. II)"

    Parameter
    ----------
    b  : Formparameter (0-1)
    k  : Wachstumsrate
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Referenzjahr
    """
    tau = np.asarray(t, float) - t0
    return np.clip(z + (C - z) * (1 - b * np.exp(-k * tau))**3, z, C)


def gompertz(t, k, C, z, t0):
    """
    Gompertz-Kurve.
    
    Quelle:
    Gompertz, B. (1825). "On the Nature of the Function Expressive of the Law of Human Mortality"

    Parameter
    ----------
    k  : Wachstumsrate
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Wendepunkt-Jahr
    """
    tau = np.asarray(t, float) - t0
    return np.clip(z + (C - z) * np.exp(-np.exp(-k * tau)), z, C)


def logistic(t, k, C, z, t0):
    """
    Logistisches Modell.

    Quelle:
    Verhulst, P. F. (1838). "Notice sur la loi que la population poursuit dans son accroissement"
    
    Parameter
    ----------
    k  : Wachstumsrate
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Wendepunkt-Jahr
    """
    tau = np.asarray(t, float) - t0
    return np.clip(z + (C - z) / (1 + np.exp(-k * tau)), z, C)


def richards_4p(t, k, d, C, z, t0):
    """
    Generalisiertes Richards-Modell, 4 Parameter.
    Spezialfall von Richards-5p mit b=1/d.
    
    Quelle:
    Richards, F. J. (1959). "A Flexible Growth Function for Empirical Use"

    Parameter
    ----------
    k  : Wachstumsrate
    d  : Formparameter (0.1-10)
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Wendepunkt-Jahr
    """
    tau   = np.asarray(t, float) - t0
    inner = np.clip(1 - (1.0 / d) * np.exp(-k * tau), 0, None)
    return np.clip(z + (C - z) * inner**d, z, C)


def richards_5p(t, b, k, d, C, z, t0):
    """
    Generalisiertes Richards-Modell, 5 Parameter (flexibelste S-Kurve).
    Enthält Bass, Bertalanffy, Gompertz und Logistisch als Spezialfälle.
    
    Quellen:
    Richards, F. J. (1959). "A Flexible Growth Function for Empirical Use"
    Höök, M. (2010). "Descriptive and Predictive Growth Curves in Energy System Analysis"

    Parameter
    ----------
    b  : Formparameter (0-1)
    k  : Wachstumsrate
    d  : Asymmetrieparameter (0.1-10)
    C  : Sättigungsniveau
    z  : vertikaler Shift
    t0 : Wendepunkt-Jahr
    """
    tau   = np.asarray(t, float) - t0
    inner = np.clip(1 - b * np.exp(-k * tau), 0, None)
    return np.clip(z + (C - z) * inner**d, z, C)


# =============================================================================
# BI-S-KURVEN
# Lineare Superposition zweier Instanzen desselben Modells.
# Bildet zweiphasige Diffusion ab (z.B. Pionier-Phase + Massenmarkt-Phase).
# Constraint: C2 ≥ C1 (zweite Phase sättigt mindestens so hoch wie erste).
# w ∈ [0,1]: Gewicht der ersten Phase.
# =============================================================================

def bi_bass(t, w, p1, q1, C1, z1, t01, p2, q2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des Bass-Modells."""
    return w * bass(t, p1, q1, C1, z1, t01) + (1 - w) * bass(t, p2, q2, C2, z2, t02)


def bi_bertalanffy(t, w, b1, k1, C1, z1, t01, b2, k2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des Bertalanffy-Modells."""
    return (w * bertalanffy(t, b1, k1, C1, z1, t01) +
            (1 - w) * bertalanffy(t, b2, k2, C2, z2, t02))


def bi_gompertz(t, w, k1, C1, z1, t01, k2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des Gompertz-Modells."""
    return (w * gompertz(t, k1, C1, z1, t01) +
            (1 - w) * gompertz(t, k2, C2, z2, t02))


def bi_logistic(t, w, k1, C1, z1, t01, k2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des logistischen Modells."""
    return (w * logistic(t, k1, C1, z1, t01) +
            (1 - w) * logistic(t, k2, C2, z2, t02))


def bi_richards_4p(t, w, k1, d1, C1, z1, t01, k2, d2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des Richards-4p-Modells."""
    return (w * richards_4p(t, k1, d1, C1, z1, t01) +
            (1 - w) * richards_4p(t, k2, d2, C2, z2, t02))


def bi_richards_5p(t, w, b1, k1, d1, C1, z1, t01, b2, k2, d2, C2, z2, t02):
    """Bi-S-Kurve auf Basis des Richards-5p-Modells."""
    return (w * richards_5p(t, b1, k1, d1, C1, z1, t01) +
            (1 - w) * richards_5p(t, b2, k2, d2, C2, z2, t02))


# =============================================================================
# MODELL-REGISTRY
# =============================================================================

UNIFORM_MODELS = [
    "Bass", "Bertalanffy", "Gompertz",
    "Logistisch", "Richards-4p", "Richards-5p",
]

BI_MODELS = [
    "Bi-Bass", "Bi-Bertalanffy", "Bi-Gompertz",
    "Bi-Logistisch", "Bi-Richards-4p", "Bi-Richards-5p",
]

ALL_MODELS = UNIFORM_MODELS + BI_MODELS

MODEL_FNS = {
    "Bass":           bass,
    "Bertalanffy":    bertalanffy,
    "Gompertz":       gompertz,
    "Logistisch":     logistic,
    "Richards-4p":    richards_4p,
    "Richards-5p":    richards_5p,
    "Bi-Bass":        bi_bass,
    "Bi-Bertalanffy": bi_bertalanffy,
    "Bi-Gompertz":    bi_gompertz,
    "Bi-Logistisch":  bi_logistic,
    "Bi-Richards-4p": bi_richards_4p,
    "Bi-Richards-5p": bi_richards_5p,
}


def get_bounds_and_p0(model_name: str, C_lo: float, C_hi: float, z_hi: float):
    """
    Gibt Parameter-Bounds und Startwerte für ein Modell zurück.
    Nach Supplementary A.6 von Zielonka et al.

    Bounds-Regeln (nach Paper):
      - C ∈ [letzter historischer Wert, technisches Potenzial]
      - t0 ∈ [2000, 2100] für Bass/Gompertz/Logistisch
        t0 ∈ [1900, 2100] für Bertalanffy/Richards (längere Diffusionshistorie)
      - b, k, p, q ∈ [0, 1]
      - d ∈ [0.1, 10]
      - z ∈ [0, erster historischer Wert]

    Parameter
    ----------
    model_name : str   Name des Modells (aus ALL_MODELS)
    C_lo       : float Untergrenze für C (= letzter historischer Wert)
    C_hi       : float Obergrenze für C (= technisches Potenzial oder Fallback)
    z_hi       : float Obergrenze für z (= erster historischer Wert)

    Returns
    -------
    lb : list  untere Parametergrenzen
    ub : list  obere Parametergrenzen
    p0 : list  Startwerte
    """
    t0A_lo, t0B_lo, t0_hi = 2000, 1900, 2100

    specs = {
        "Bass":        (
            [1e-5, 1e-5, C_lo, 0, t0A_lo],
            [1.0,  1.0,  C_hi, z_hi, t0_hi],
            [0.01, 0.2,  C_lo * 1.5, 0, 2020],
        ),
        "Bertalanffy": (
            [0,    1e-5, C_lo, 0, t0B_lo],
            [1.0,  1.0,  C_hi, z_hi, t0_hi],
            [0.5,  0.1,  C_lo * 1.5, 0, 2010],
        ),
        "Gompertz":    (
            [1e-5, C_lo, 0, t0A_lo],
            [1.0,  C_hi, z_hi, t0_hi],
            [0.2,  C_lo * 1.5, 0, 2020],
        ),
        "Logistisch":  (
            [1e-5, C_lo, 0, t0A_lo],
            [1.0,  C_hi, z_hi, t0_hi],
            [0.2,  C_lo * 1.5, 0, 2030],
        ),
        "Richards-4p": (
            [1e-5, 1e-3, C_lo, 0, t0B_lo],
            [1.0,  10.0, C_hi, z_hi, t0_hi],
            [0.2,  1.5,  C_lo * 1.5, 0, 2025],
        ),
        "Richards-5p": (
            [0,    1e-5, 1e-3, C_lo, 0, t0B_lo],
            [1.0,  1.0,  10.0, C_hi, z_hi, t0_hi],
            [0.5,  0.2,  1.5,  C_lo * 1.5, 0, 2025],
        ),
    }

    if model_name in specs:
        lb, ub, p0 = specs[model_name]
        return list(lb), list(ub), list(p0)

    # Bi-Modelle: w ∈ [0,1] + doppelte Parameter des Basismodells
    base = model_name.replace("Bi-", "")
    lb_b, ub_b, p0_b = specs[base]
    return (
        [0.0] + lb_b + lb_b,
        [1.0] + ub_b + ub_b,
        [0.5] + p0_b + p0_b,
    )
