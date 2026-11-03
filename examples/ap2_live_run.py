"""AP3.1 → AP2 Live-Run für Reichshof (05374040).

Ausführen aus dem ObjectTypeGenerator-Verzeichnis (dort liegt das uv-venv + src/):
    cd ~/coding/simuflex/hochlauf/objekttypegenerator
    uv run python ~/coding/simuflex/hochlauf/hochlauf_model/pv_hochlauf/ap2_live_run.py <out.json>
Voraussetzung: lokale InfDB läuft (podman, Port 54328) mit basedata/ro_heat für die AGS
(siehe ap3_1_hochlaufszenarien/infdb_local_setup.md) und hochlauf.sqlite mit dem AP3.1-Band.


Koppelt das AP3.1-PV-Hochlaufband (installierte MWp, Zielonka-Ensemble) an den
ObjectTypeGenerator (AP2): der PV-`total` (Haushaltsanteil) wird so kalibriert,
dass die von AP2 resultierende installierte Σ MWp die AP3.1-Zielkapazität trifft
(Kopplung über die physikalische Größe, nicht über eine Ø-kWp-Annahme).
Struktur (Haustyp×Eigentum×Gemeindetyp×Baualter) bleibt KfW/IPF.
"""
from __future__ import annotations
import dataclasses, json, sqlite3, sys
from pathlib import Path

import pandas as pd
from objecttypegenerator.adapters.parameter_files import (
    load_construction_period_shares, load_design_temperatures, load_technologies,
    load_run_configuration, resolve_path)
from objecttypegenerator.adapters.zensus_csv import load_census_tables
from objecttypegenerator.adapters.infdb import connect_to_infdb, InfdbBuildingSource
from objecttypegenerator.application.pipeline import run_generation
from objecttypegenerator.application.reference_data import prepare_reference_data
from objecttypegenerator.application.settings import RunSettings
from objecttypegenerator.domain.technologies import CalibratedTechnology
from objecttypegenerator.domain.errors import CalibrationError

AGS = "05374040"  # Reichshof
PKG = Path("src/objecttypegenerator/data")
ADDINFO = Path("additional-information")
SQLITE = Path("../hochlauf_model/hochlauf.sqlite")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ap2_coupling.json")

settings = RunSettings(seed=42)

# --- AP3.1-Band (Reichshof, PV, raum_id=138) aus unserer hochlauf.sqlite ---
con = sqlite3.connect(SQLITE)
band = {(sj, q): w for sj, q, w in con.execute(
    "select stuetzjahr, quantil, wert from diffusion_ensemble "
    "where raum_id=138 and technologie_id=1")}  # MWp
con.close()

# --- Reichshof-Gebäudeframe aus InfDB ---
config = load_run_configuration(Path("configs/config-objecttypegenerator.yml"))
engine = connect_to_infdb(config.database)
source = InfdbBuildingSource(engine, input_schema="basedata", heat_loss_schema="ro_heat")
frame = source.load(AGS)
print(f"InfDB-Frame: {len(frame)} Gebäude", file=sys.stderr)

# --- Referenz-Inputs ---
census = load_census_tables(ADDINFO)
technologies = load_technologies(resolve_path("package:kfw/kfw_2025.yaml", Path.cwd()))
constr = load_construction_period_shares(resolve_path("package:kfw/construction_period_shares.yaml", Path.cwd()))
design = load_design_temperatures(resolve_path("package:din_en_12831/design_temperatures.csv", Path.cwd()))
PV_BASE = next(t for t in technologies if t.name == "pv").total  # 0.16


def with_pv_total(t: float):
    return tuple(dataclasses.replace(s, total=t) if (isinstance(s, CalibratedTechnology) and s.name == "pv")
                 else s for s in technologies)


def run(pv_total: float) -> dict:
    ref = prepare_reference_data(census, with_pv_total(pv_total), constr, design, settings=settings)
    res = run_generation(frame, ref, settings)
    b, h = res.buildings, res.households
    pv = b[b.pv_vorhanden]
    mwp = float(pv.pv_leistung_kwp.sum()) / 1000.0
    obj = h.objekttyp.value_counts()
    return {
        "pv_total_input": round(pv_total, 5),
        "n_buildings": int(len(b)),
        "n_households": int(len(h)),
        "pv_buildings": int(b.pv_vorhanden.sum()),
        "pv_share_buildings": round(float(b.pv_vorhanden.mean()), 4),
        "pv_mwp": round(mwp, 3),
        "pv_mean_kwp": round(float(pv.pv_leistung_kwp.mean()), 2) if len(pv) else None,
        "battery_buildings": int(b.batterie_vorhanden.sum()),
        "heatpump_buildings": int(b.waermepumpe_vorhanden.sum()),
        "heatpump_mw": round(float(b[b.waermepumpe_vorhanden].waermepumpe_leistung_kw.sum()) / 1000.0, 3),
        "ev_households": int(h.eauto_vorhanden.sum()),
        "ev_share_hh": round(float(h.eauto_vorhanden.mean()), 4),
        "balcony_households": int(h.balkonkraftwerk_vorhanden.sum()),
        "objekttyp_top": {str(k): int(v) for k, v in obj.head(8).items()},
    }


def try_run(t: float):
    try:
        return run(t)
    except CalibrationError:
        return None


def max_feasible_total(lo: float = 0.16, hi: float = 0.95) -> tuple[float, dict]:
    """Höchster PV-total, den die fixe KfW-Struktur per IPF noch zulässt (Bisektion)."""
    best_t, best_r = lo, try_run(lo)
    for _ in range(18):
        mid = (lo + hi) / 2.0
        r = try_run(mid)
        if r is None:
            hi = mid
        else:
            lo, best_t, best_r = mid, mid, r
    return best_t, best_r


def calibrate_to_mwp(target_mwp: float, m_ref: float, t_ref: float, t_max: float, m_max: float) -> dict:
    """PV-total so wählen, dass Σ MWp ≈ target (linear + 1 Verfeinerung).
    Liegt das Ziel über der Struktur-Decke, als nicht erreichbar markieren."""
    if target_mwp > m_max + 0.05:
        return {"ap31_target_mwp": round(target_mwp, 3), "machbar": False,
                "grund": "uebersteigt KfW-Struktur-Decke", "decke_mwp": round(m_max, 3),
                "decke_pv_total": round(t_max, 4), "luecke_mwp": round(target_mwp - m_max, 3)}
    t = min(max(t_ref * target_mwp / m_ref, 1e-4), t_max)
    r = try_run(t) or {}
    if r.get("pv_mwp", 0) > 0:
        t = min(max(t * target_mwp / r["pv_mwp"], 1e-4), t_max)
        r = try_run(t) or r
    r["ap31_target_mwp"] = round(target_mwp, 3)
    r["machbar"] = True
    return r

# --- Baseline (KfW heute, national) ---
results = {"ags": AGS, "gemeinde": "Reichshof", "pv_total_kfw_base": PV_BASE,
           "households_infdb": int(frame.households.fillna(0).sum()) if "households" in frame else None,
           "scenarios": {}}
base = run(PV_BASE)
results["scenarios"]["kfw_basis"] = base
m_ref, t_ref = base["pv_mwp"], PV_BASE
print(f"Baseline KfW total={PV_BASE}: {base['pv_buildings']} PV-Gebäude, {base['pv_mwp']} MWp", file=sys.stderr)

# --- Struktur-Decke (höchste mit fixer KfW-Struktur erreichbare Durchdringung) ---
t_max, r_max = max_feasible_total()
results["struktur_decke"] = {"pv_total": round(t_max, 4), "pv_mwp": r_max["pv_mwp"],
                             "pv_buildings": r_max["pv_buildings"],
                             "pv_share_buildings": r_max["pv_share_buildings"]}
m_max = r_max["pv_mwp"]
print(f"Struktur-Decke: total={t_max:.3f} → {m_max} MWp ({r_max['pv_buildings']} Gebäude)", file=sys.stderr)

# --- AP3.1 p50-Trajektorie ---
for sj in (2025, 2030, 2035, 2040, 2045, 2050):
    tgt = band.get((sj, 0.5))
    if tgt is None:
        continue
    results["scenarios"][f"ap31_p50_{sj}"] = calibrate_to_mwp(tgt, m_ref, t_ref, t_max, m_max)
    print(f"AP3.1 p50 {sj}: Ziel {tgt} MWp", file=sys.stderr)

# --- AP3.1 Szenario-Fächer 2040 (konservativ p25 / referenz p50 / ambitioniert p75) ---
for q, label in ((0.25, "konservativ"), (0.5, "referenz"), (0.75, "ambitioniert")):
    tgt = band.get((2040, q))
    if tgt is None:
        continue
    results["scenarios"][f"ap31_2040_{label}"] = calibrate_to_mwp(tgt, m_ref, t_ref, t_max, m_max)

OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(f"\nGeschrieben: {OUT}", file=sys.stderr)
print(json.dumps(results["scenarios"], indent=2, ensure_ascii=False))
