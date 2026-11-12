"""AP3.1 → AP2 Verteilung mit Struktur-Konvergenz (Baustein 2).

Je Szenario × Stützjahr:
  1. alpha aus dem Szenario-Schedule (structure.py) → PV-Margins Richtung gleichmäßig.
  2. `total` so kalibrieren, dass die von AP2 verteilte Σ PV-Leistung das AP3.1-Band-Ziel trifft
     (AP2 sized dachgedeckelt, Baustein 1).
  3. AP2-Lauf, Ergebnis je Gebäude + Aufschlüsselung speichern.

Ausführen aus dem ObjectTypeGenerator-Verzeichnis (dessen venv hat AP2):
    cd ~/coding/simuflex/hochlauf/objekttypegenerator
    uv run python ~/coding/simuflex/hochlaufszenarien/coupling/distribute.py \
        --band ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_band.csv \
        --ags 05374040 --out /tmp/ap2_scenarios.json
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd, sqlalchemy

from objecttypegenerator.adapters.parameter_files import (
    load_construction_period_shares, load_design_temperatures, load_technologies, resolve_path)
from objecttypegenerator.adapters.zensus_csv import load_census_tables
from objecttypegenerator.adapters.infdb import InfdbBuildingSource
from objecttypegenerator.application.pipeline import run_generation
from objecttypegenerator.application.reference_data import prepare_reference_data
from objecttypegenerator.application.settings import RunSettings
from objecttypegenerator.domain.errors import CalibrationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from structure import pv_with_structure  # noqa: E402

SCEN_QUANTILE = {"konservativ": "p25_MWp", "referenz": "p50_MWp", "ambitioniert": "p75_MWp"}
STUETZJAHRE = [2025, 2030, 2035, 2040, 2045, 2050]
PV_PACKAGE_DEFAULT = "additional-information"
# PV-total deckeln: darüber bleiben zu wenige PV-lose Haushalte für balcony_pv (excluded_by pv).
# 0,95 liegt weit über dem, was die MWp-Ziele brauchen (dachbegrenzt << 95 % Durchdringung).
MAX_TOTAL = 0.95


def load_inputs(dsn: str, ags: str):
    settings = RunSettings(seed=42)
    frame = InfdbBuildingSource(sqlalchemy.create_engine(dsn),
                                input_schema="basedata", heat_loss_schema="ro_heat").load(ags)
    census = load_census_tables(Path(PV_PACKAGE_DEFAULT))
    techs = load_technologies(resolve_path("package:kfw/kfw_2025.yaml", Path.cwd()))
    constr = load_construction_period_shares(resolve_path("package:kfw/construction_period_shares.yaml", Path.cwd()))
    design = load_design_temperatures(resolve_path("package:din_en_12831/design_temperatures.csv", Path.cwd()))
    base_total = next(t for t in techs if t.name == "pv").total
    return settings, frame, (census, techs, constr, design), base_total


def run_once(frame, inputs, settings, total: float, alpha: float):
    census, techs, constr, design = inputs
    ref = prepare_reference_data(census, pv_with_structure(techs, total=total, alpha=alpha),
                                 constr, design, settings=settings)
    return run_generation(frame, ref, settings).buildings


def _mwp(buildings) -> float:
    return float(buildings.loc[buildings.pv_vorhanden, "pv_leistung_kwp"].sum()) / 1000.0


def _solve_total(frame, inputs, settings, *, target_mwp, alpha, base_total):
    """Bei festem alpha `total` per Bisektion so wählen, dass Σ MWp ≈ Ziel. Robust gegen Überschießen:
    ein CalibrationError (z. B. balcony_pv bei zu hoher Durchdringung) gilt als 'total zu hoch'.
    Gibt (t, buildings, m) zurück; bleibt m < Ziel, ist das Ziel bei diesem alpha nicht erreichbar."""
    lo, hi = base_total, MAX_TOTAL
    best = None  # (t, b, m), höchstes erreichtes m
    for _ in range(12):
        mid = (lo + hi) / 2.0
        try:
            b = run_once(frame, inputs, settings, mid, alpha)
            m = _mwp(b)
        except CalibrationError:
            hi = mid  # zu hoch (IPF/balcony) → Obergrenze senken
            continue
        if best is None or m > best[2]:
            best = (mid, b, m)
        if abs(m - target_mwp) <= 0.1:
            return mid, b, m
        if m < target_mwp:
            lo = mid
        else:
            hi = mid
    if best is None:  # selbst base_total bricht → erzwinge ein Ergebnis am unteren Rand
        b = run_once(frame, inputs, settings, base_total, alpha)
        best = (base_total, b, _mwp(b))
    return best


def calibrate(frame, inputs, settings, *, target_mwp, base_total, alpha_step=0.1):
    """Kleinstes alpha (Struktur-Angleichung) finden, bei dem sich das MWp-Ziel real unterbringen
    lässt — alpha ist damit ein Ergebnis, keine Annahme. Pro alpha wird `total` kalibriert."""
    a = 0.0
    last = None
    while True:
        try:
            t, b, m = _solve_total(frame, inputs, settings, target_mwp=target_mwp,
                                   alpha=a, base_total=base_total)
            last = (t, a, b)
            if m >= target_mwp - 0.1:
                return t, a, b
        except CalibrationError:
            pass
        if a >= 1.0:  # auch volle Angleichung reicht nicht (dachbegrenzt) → bestes Ergebnis
            if last is None:
                try:
                    b = run_once(frame, inputs, settings, MAX_TOTAL, 1.0)
                except CalibrationError:
                    b = run_once(frame, inputs, settings, 0.5, 1.0)
                last = (MAX_TOTAL, 1.0, b)
            return last
        a = round(min(1.0, a + alpha_step), 2)


def _breakdown(b) -> dict:
    g = b.copy()
    g["gruppe"] = np.where(g.haustyp.isin(["MFH", "AB"]), "MFH",
                           np.where(g.eigentuemeranteil >= 0.5, "EFH_Eigentuemer", "EFH_Mieter"))
    out = {}
    for name, sub in g.groupby("gruppe"):
        pv = sub[sub.pv_vorhanden]
        out[name] = {"gebaeude": int(len(sub)), "mit_pv": int(sub.pv_vorhanden.sum()),
                     "mwp": round(float(pv.pv_leistung_kwp.sum()) / 1000.0, 2)}
    return out


def run_scenarios(band_csv: str, ags: str, dsn: str, out_json: str, per_building_csv: str | None):
    band = pd.read_csv(band_csv).set_index("jahr")
    settings, frame, inputs, base_total = load_inputs(dsn, ags)
    print(f"Frame: {len(frame)} Gebäude (AGS {ags}) | KfW-Basis total={base_total}", file=sys.stderr)
    result = {"ags": ags, "hinweis": "alpha = minimal noetige Struktur-Angleichung (0=KfW2025, 1=gleichmaessig)",
              "szenarien": {}}
    for scen, col in SCEN_QUANTILE.items():
        result["szenarien"][scen] = {}
        for yr in STUETZJAHRE:
            if yr not in band.index:
                continue
            target = float(band.loc[yr, col])
            t, a, b = calibrate(frame, inputs, settings, target_mwp=target, base_total=base_total)
            ist = _mwp(b)
            rec = {"ziel_mwp": round(target, 2), "ist_mwp": round(ist, 2),
                   "pv_total": round(t, 4), "alpha": round(a, 3),
                   "erreicht": ist >= target - 0.15,
                   "pv_gebaeude": int(b.pv_vorhanden.sum()),
                   "aufschluesselung": _breakdown(b)}
            result["szenarien"][scen][yr] = rec
            flag = "" if rec["erreicht"] else "  (dachbegrenzt, nicht erreicht)"
            print(f"{scen:12s} {yr}: Ziel {target:5.1f} → ist {ist:5.1f} MWp | "
                  f"alpha {a:.2f} | {rec['pv_gebaeude']} Geb.{flag}", file=sys.stderr)
            # Pro-Gebäude-Export nur für referenz 2040 (für die Karte)
            if per_building_csv and scen == "referenz" and yr == 2040:
                b.to_csv(per_building_csv, index=False)
    Path(out_json).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"\nGeschrieben: {out_json}", file=sys.stderr)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--band", required=True, help="Band-CSV (jahr, p05_MWp … p95_MWp)")
    p.add_argument("--ags", default="05374040")
    p.add_argument("--dsn", default="postgresql+psycopg2://infdb_user:infdb@127.0.0.1:54328/infdb")
    p.add_argument("--out", default="/tmp/ap2_scenarios.json")
    p.add_argument("--per-building", default=None, help="CSV-Export der referenz-2040-Verteilung")
    a = p.parse_args()
    run_scenarios(a.band, a.ags, a.dsn, a.out, a.per_building)


if __name__ == "__main__":
    main()
