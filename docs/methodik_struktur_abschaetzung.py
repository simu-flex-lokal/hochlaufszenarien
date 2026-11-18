"""Grobe Abschätzung: gruppenspezifische Sättigung + gemeinsame Marktgeschwindigkeit h(t), Summe = Band (PV-Gebäude)."""
# Skizze zu docs/methodik_struktur_vorschlag.md, Abschnitt 4. Ausführen: python docs/methodik_struktur_abschaetzung.py
import numpy as np

def brentq(f, a, b):
    for _ in range(200):
        m = (a + b) / 2
        if (f(a) < 0) == (f(m) < 0): a = m
        else: b = m
    return (a + b) / 2

def run(N, p0, S, r, targets, years=range(2026, 2051)):
    N, p, S, r = map(np.asarray, (N, p0, S, r)); p = p.astype(float).copy()
    p *= targets[2025] / (N @ p)                       # Start = Istwert (Struktur KfW, Niveau MaStR)
    ys = sorted(targets); hs = {}
    for y in years:
        tgt = np.interp(y, ys, [targets[k] for k in ys])
        f = lambda h: N @ (p + (1 - np.exp(-r * h)) * (S - p)) - tgt
        if f(60) < 0: return p, hs, y                   # Band über dem Gruppenpotenzial
        h = brentq(f, 0, 60) if f(0) < 0 else 0.0
        p = p + (1 - np.exp(-r * h)) * (S - p); hs[y] = h
    return p, hs, None

gemeinden = {  # N: EFH-Eigentümer, EFH-Mieter, MFH (Gebäude, InfDB develop); Ziel: PV-Gebäude ≈ Band p50 / 9,1 kWp
    "Reichshof":   ([4016, 596, 1668], {2025: 1035, 2030: 1527, 2040: 2132, 2050: 2473}),
    "Wipperfürth": ([3236, 535, 2033], {2025: 1323, 2030: 1901, 2040: 2758, 2050: 3264}),
}
p_kfw = [0.34, 0.09, 0.07]          # KfW 2025 Tab. 4 (MFH: Mittel Wohnung Eigentum 9 % / Mieter 6 %)
for szen, S, r in [("Status quo (Mieter/MFH-Hürden bleiben)", [0.72, 0.50, 0.50], [1.0, 0.12, 0.15]),
                   ("Hürden sinken (Gebäudestrom §42b wirkt)", [0.72, 0.60, 0.60], [1.0, 0.40, 0.40])]:
    print("==", szen, " S =", S, " r =", r)
    for g, (N, tg) in gemeinden.items():
        p, hs, fail = run(N, p_kfw, S, r, tg)
        msg = f"  Band ab {fail} nicht erreichbar" if fail else ""
        print(f"  {g:12s} 2050: EFH-Eig {p[0]:.0%}  EFH-Miet {p[1]:.0%}  MFH {p[2]:.0%}  "
              f"| h 2030 {hs.get(2030, float('nan')):.3f}, 2045 {hs.get(2045, float('nan')):.3f}{msg}")
