"""Struktur-Konvergenz für die AP3.1→AP2-Kopplung.

AP2 verteilt PV nach der KfW-2025-Querschnittsstruktur (Haustyp×Eigentum). Diese Struktur ist für
*heute* gefittet; für den Hochlauf muss sie sich über die Zeit angleichen, sonst sättigen die
Vorreiter (Eigentümer-EFH) lange vor dem Kapazitätsziel und die Nachzügler (Mieter/MFH) bleiben
unrealistisch leer.

Wir mischen die Haustyp×Eigentum-Margins der PV über einen Parameter ``alpha`` von KfW 2025
(``alpha=0``) Richtung gleichmäßig (``alpha=1``). ``alpha`` wird in der Kalibrierung (distribute.py)
*nicht gesetzt*, sondern als die **minimal nötige Angleichung** bestimmt, um die AP3.1-Kapazität
real auf den Gebäuden/Dächern unterzubringen — ein Ergebnis, keine Annahme. AP2 bleibt unverändert,
wir überschreiben nur den PV-Technologie-Spec.
"""
from __future__ import annotations
import dataclasses
import numpy as np

from objecttypegenerator.domain.technologies import CalibratedTechnology


def _blend_to_uniform(shares: np.ndarray, alpha: float) -> np.ndarray:
    """Mischt die Shares Richtung ihres Mittelwerts (gleichmäßig), Level bleibt erhalten."""
    uniform = np.full_like(shares, shares.mean())
    return (1.0 - alpha) * shares + alpha * uniform


def pv_with_structure(technologies, *, total: float, alpha: float):
    """Technologie-Tuple mit überschriebenem PV-Spec: `total` gesetzt, **alle** PV-Margins um `alpha`
    Richtung gleichmäßig gemischt (Haustyp×Eigentum UND Gemeindetyp — letztere ist für einen
    Ein-Gemeinde-Lauf nur ein konstanter Offset, der sonst das erreichbare Niveau deckelt).

    Liegt `total` unter dem KfW-Wert, sinkt der Batterie-Anteil im selben Verhältnis: Batterien setzen PV
    voraus (``requires: pv``), ihr Anteil an den PV-Gebäuden bleibt so beim KfW-Wert (9 von 16 %). Sonst
    hätten mehr Gebäude eine Batterie als PV. Darüber und für alle anderen Technologien: unverändert."""
    kfw_total = next(t.total for t in technologies if t.name == "pv")
    battery_scale = min(1.0, total / kfw_total)
    out = []
    for spec in technologies:
        if isinstance(spec, CalibratedTechnology) and spec.name == "pv":
            margins = tuple(dataclasses.replace(m, shares=_blend_to_uniform(m.shares, alpha))
                            for m in spec.margins)
            out.append(dataclasses.replace(spec, total=total, margins=margins))
        elif isinstance(spec, CalibratedTechnology) and spec.name == "battery":
            out.append(dataclasses.replace(spec, total=spec.total * battery_scale))
        else:
            out.append(spec)
    return tuple(out)
