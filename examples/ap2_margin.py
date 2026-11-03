"""ap2_margin.py — Phase 3: AP-3.1-Rand für den ObjektTypeGenerator (AP 2).

Erzeugt aus dem persistierten Zielonka-Ensemble-Band (``diffusion_ensemble``, MWp)
den **Ziel-Rand**, den AP 2 als Technologie-``total`` (Durchdringungsanteil) konsumiert:

    Durchdringung(Gemeinde, Stützjahr, Szenario) = Anzahl / Wohngebäude
    Anzahl = Bestand[MWp] · 1000 / Ø-Anlagengröße[kWp]

**Szenario ↔ Quantil (vorläufig):** konservativ = p25 · referenz = p50 · ambitioniert = p75.
Das ist ein pragmatischer Erstbezug (Band = Prognose­unsicherheit); die normative §14a-Schicht
(eigene Achse) ersetzt diese Zuordnung in Phase 2-final.

**Einschränkungen (ehrlich):** Die MWp→Anzahl-Umrechnung mit einer mittleren Ø-Größe ist eine
Näherung — produktiv liefert das Ensemble die Anzahl direkt (Lauf auf ``Anlagen_kum``). Und AP 2s
``total`` ist der Anteil an *Haushalten*; hier ist der Nenner *Wohngebäude* (für PV die natürliche
Basis). Beides ist beim Verschalten mit AP 2 final abzustimmen.

    python hochlauf_model/pv_hochlauf/ap2_margin.py --ags 05374040 --avg-kwp 9.06 --wohngebaeude 5900
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "hochlauf.sqlite"
SZENARIO_QUANTIL = {"konservativ": 0.25, "referenz": 0.50, "ambitioniert": 0.75}


def build_margin(db_path, ags, technologie, avg_kwp, verteilbare_gebaeude, c_hi_mwp=None):
    """Dual-Vorgabe je Szenario×Stützjahr: Durchdringung (→ AP-2 total) UND Leistung (MWp).

    Verbunden über ``avg_kwp`` (MUSS der MaStR-kWp-Verteilung entsprechen, die AP 2 zieht —
    sonst divergieren Anzahl und Leistung). Guards: Anzahl ≤ verteilbare Gebäude, MWp ≤ C_hi.
    Zusätzlich dimensionslos: Potenzial-Fraktion = MWp / C_hi (BUILDA-Dachpotenzial).
    """
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT e.stuetzjahr, e.quantil, e.wert FROM diffusion_ensemble e "
        "JOIN raumeinheit r ON r.id=e.raum_id JOIN technologie t ON t.id=e.technologie_id "
        "WHERE r.raum_code=? AND t.code=? AND e.einheit='MWp'", (ags, technologie)).fetchall()
    con.close()
    if not rows:
        raise SystemExit(f"Kein Ensemble-Band für {ags}/{technologie} — zuerst persistieren.")
    band = {}
    for yr, q, mwp in rows:
        band.setdefault(yr, {})[round(q, 2)] = mwp
    out = []
    for szen, quant in SZENARIO_QUANTIL.items():
        for yr in sorted(band):
            mwp = band[yr].get(quant)
            if mwp is None:
                continue
            anzahl = round(mwp * 1000.0 / avg_kwp)
            durchdringung = anzahl / verteilbare_gebaeude
            machbar = (anzahl <= verteilbare_gebaeude) and (c_hi_mwp is None or mwp <= c_hi_mwp)
            rec = {"gemeinde": ags, "technologie": technologie, "szenario": szen,
                   "stuetzjahr": int(yr), "quantil": quant,
                   # Dual-Vorgabe an AP 2:
                   "durchdringung": round(min(durchdringung, 1.0), 4),   # → total (Anteil Gebäude)
                   "anzahl": anzahl,                                      # N Gebäude
                   "leistung_MWp": round(mwp, 2),                         # Summen-Leistung (Konsistenz)
                   "avg_kwp": avg_kwp,                                    # verbindende Ø-Größe
                   "machbar": machbar}
            if c_hi_mwp:
                rec["potenzial_fraktion"] = round(mwp / c_hi_mwp, 3)      # MWp / Dachpotenzial
            out.append(rec)
    return out


def run(db_path, ags, technologie, avg_kwp, verteilbare_gebaeude, c_hi_mwp, outdir):
    margin = build_margin(db_path, ags, technologie, avg_kwp, verteilbare_gebaeude, c_hi_mwp)
    outdir.mkdir(parents=True, exist_ok=True)
    import csv
    cpath = outdir / f"ap2_margin_{ags}_{technologie}.csv"
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(margin[0].keys()))
        w.writeheader(); w.writerows(margin)
    (outdir / f"ap2_margin_{ags}_{technologie}.json").write_text(
        json.dumps({"basis": {"avg_kwp": avg_kwp, "verteilbare_gebaeude": verteilbare_gebaeude,
                              "c_hi_MWp": c_hi_mwp,
                              "hinweis": "avg_kwp MUSS der MaStR-kWp-Verteilung von AP 2 entsprechen"},
                    "szenario_quantil": SZENARIO_QUANTIL, "rand": margin}, indent=1, ensure_ascii=False))
    print(f"AP-2-Rand ({ags}/{technologie}) → {cpath}")
    print(f"Basis: Ø {avg_kwp} kWp · {verteilbare_gebaeude} verteilbare Gebäude"
          + (f" · Dachpotenzial {c_hi_mwp} MWp" if c_hi_mwp else ""))
    print(f"\n{'Szenario':13} {'Jahr':>5} {'MWp':>6} {'Anzahl':>7} {'Durchdr.':>8} "
          f"{'% Potenzial':>11} {'machbar':>8}")
    for r in margin:
        if r["stuetzjahr"] in (2030, 2040, 2050):
            pf = f"{r.get('potenzial_fraktion',0)*100:>9.0f} %" if c_hi_mwp else "         –"
            print(f"{r['szenario']:13} {r['stuetzjahr']:>5} {r['leistung_MWp']:>6} "
                  f"{r['anzahl']:>7} {r['durchdringung']*100:>6.1f} % {pf} {'ja' if r['machbar'] else 'NEIN':>8}")
    n_bad = sum(1 for r in margin if not r["machbar"])
    print(f"\nMachbarkeit: {len(margin)-n_bad}/{len(margin)} Vorgaben erfüllbar"
          + (f" — {n_bad} überschreiten Gebäude/Dachpotenzial!" if n_bad else "."))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--ags", required=True)
    p.add_argument("--technologie", default="pv")
    p.add_argument("--avg-kwp", type=float, required=True,
                   help="Ø-Anlagengröße [kWp] — MUSS der MaStR-kWp-Verteilung von AP 2 entsprechen")
    p.add_argument("--verteilbare-gebaeude", type=int, required=True,
                   help="Gebäude, über die AP 2 verteilt (Zensus Wohngebäude / InfDB / pylovo)")
    p.add_argument("--c-hi", type=float, default=None, help="Dachpotenzial [MWp] (BUILDA) für Potenzial-Fraktion + Guard")
    p.add_argument("--outdir", type=Path, default=Path("data/pv_hochlauf/outputs/ap2"))
    args = p.parse_args(argv)
    run(args.db.resolve(), args.ags, args.technologie, args.avg_kwp, args.verteilbare_gebaeude,
        args.c_hi, args.outdir.resolve())


if __name__ == "__main__":
    main()
