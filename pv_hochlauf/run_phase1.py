"""run_phase1.py — Phase-1-Smoke-Test der Zielonka-Pipeline an unserer Datenquelle.

Fährt die 4-Schritte-Pipeline für eine Zielgemeinde (Default Jülich 05358024) mit
NRW als Referenzpool, Daten aus dem OEDS (db_adapter) statt Pickle.

Sättigung C_hi der Zielgemeinde (``--saturation``):
  infdb   (Standard) Dachpotenzial der Wohngebäude aus der InfDB — dieselbe Datenbasis wie AP 2
          und die Netzsimulation (pylovo); siehe io/infdb_saturation.py
  builda  ETHOS.BUILDA über die API (alt, nur noch zum Vergleich)
  default 5 × letzter Bestand
Die Vergleichsgemeinden nutzen immer den Default-Multiplikator.

Aufruf:
    python pv_hochlauf/run_phase1.py --target 05374040
"""
from __future__ import annotations

import argparse
import time

# --- Config VOR den Pipeline-Imports setzen (Werte werden beim Import gebunden) ---
import pv_hochlauf.core.config as cfg


def _configure(fast: bool, saturation: str):
    cfg.USE_BUILDA_SATURATION = saturation == "builda"
    cfg.FORCE_RECOMPUTE = True
    cfg.SAVE_DET_PROJ = False
    if fast:
        cfg.DE_MAXITER = 40
        cfg.DE_POPSIZE = 6
        cfg.MAX_AHEAD_YRS = 8
        cfg.N_SCENARIO_PATHS = 20
        cfg.HINDCAST_MAX_SIMILAR = 80


def run(target: str, bundesland: str, fast: bool, saturation: str, infdb_dsn: str):
    _configure(fast, saturation)
    # Imports erst JETZT (binden die gesetzten Config-Werte)
    from pv_hochlauf.io.db_adapter import load_mastr_pv
    from pv_hochlauf.io.database import prepare_timeseries, filter_timeseries
    from pv_hochlauf.pipeline.fitting import step1_deterministic_parallel
    from pv_hochlauf.pipeline.probabilistic import step2_probabilistic
    from pv_hochlauf.pipeline.hindcasting import step3_hindcasting
    from pv_hochlauf.pipeline.ensemble import step4_ensemble
    import numpy as np
    import pandas as pd

    t0 = time.time()
    df = load_mastr_pv(bundesland=bundesland)
    ts_all = prepare_timeseries(df)
    valid, excl = filter_timeseries(ts_all, metric="kW_kum")
    if target not in valid:
        raise SystemExit(f"Ziel {target} nicht im validen Pool "
                         f"(in Daten: {target in ts_all}, ausgeschlossen: {target in excl}).")

    # Sättigung C_hi nur für die Zielgemeinde — Pool: Default-Multiplikator
    metadata_df = None
    c_hi_source = "default"
    if saturation == "infdb":
        from pv_hochlauf.io.infdb_saturation import fetch_infdb_roof_potential
        from pv_hochlauf.io.saturation import build_metadata_df
        roof = fetch_infdb_roof_potential(target, infdb_dsn)
        print(f"\n[0] {roof.summary()}")
        metadata_df = build_metadata_df({target: roof.c_hi_kwp})
        c_hi_source = f"infdb/{roof.source}"
    elif saturation == "builda":
        from pv_hochlauf.io.saturation import fetch_builda_saturation_bulk, build_metadata_df
        c_hi_source = "builda"
        grp = df[df["Gemeindeschluessel"] == target]
        cities = {target: {
            "Gemeinde": grp["Gemeinde"].iloc[0],
            "Postleitzahl": [str(p) for p in grp["Postleitzahl"].dropna().unique()],
        }}
        print(f"\n[0] BUILDA-Dachflächen-Sättigung für {target} "
              f"({cities[target]['Gemeinde']}, PLZ {cities[target]['Postleitzahl']}) ...")
        sat = fetch_builda_saturation_bulk(cities)
        metadata_df = build_metadata_df(sat)
        c_hi_builda = sat.get(target)
        c_hi_default = float(valid[target]["kW_kum"].iloc[-1]) * 5.0
        print(f"  C_hi (BUILDA)  = {(c_hi_builda or 0)/1000:.1f} MWp"
              f"   vs. Default 5×Ist = {c_hi_default/1000:.1f} MWp")

    print(f"\n[1] Deterministische Fits: {len(valid)} Gemeinden (Referenzpool) ...")
    det = step1_deterministic_parallel(valid, metric="kW_kum", metadata_df=metadata_df,
                                       proj_end=cfg.PROJ_END)
    print(f"[2] Probabilistik für {target} ...")
    prob = step2_probabilistic(det, target_gemeinden=[target])
    print(f"[3] Hindcasting (MAPE/WIS) für {target} ...")
    weights, scores = step3_hindcasting(det, target_gemeinden=[target])
    print(f"[4] Ensemble ...")
    ens = step4_ensemble(prob, weights)

    # --- Ergebnis für die Zielgemeinde ---
    e = ens[target]
    t = e["t_proj"]
    jahre = [2025, 2030, 2035, 2040, 2045, 2050]
    print(f"\n=== {target}: PV-Hochlauf (MWp), Ensemble-Quantile ===")
    print(f"{'Jahr':>6} {'p05':>9} {'p50 (Median)':>14} {'p95':>9}")
    for yr in jahre:
        if yr < t[0] or yr > t[-1]:
            continue
        i = int(np.argmin(np.abs(t - yr)))
        p05 = e["quantiles"][0.05][i] / 1000
        p50 = e["quantiles"][0.50][i] / 1000
        p95 = e["quantiles"][0.95][i] / 1000
        print(f"{yr:>6} {p05:>9.1f} {p50:>14.1f} {p95:>9.1f}")

    hist_last = e["last_val"] / 1000
    print(f"\nIst-Bestand {int(e['t_proj'][0])}+: zuletzt {hist_last:.1f} MWp "
          f"| ähnliche Gemeinden: {prob[target]['n_similar']}")
    top = sorted(weights[target].items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("Top-gewichtete Modelle (Hindcast):",
          ", ".join(f"{m} {w*100:.0f}%" for m, w in top))

    # Band-Export (alle Jahre, 5 Quantile) für das Ergebnis-Artefakt
    out = cfg.OUT_CSV / f"band_{target}.csv"
    cfg.OUT_CSV.mkdir(parents=True, exist_ok=True)
    rows = {"jahr": t.astype(int)}
    for q in (0.05, 0.25, 0.50, 0.75, 0.95):
        rows[f"p{int(q*100):02d}_MWp"] = np.round(e["quantiles"][q] / 1000, 2)
    pd.DataFrame(rows).to_csv(out, index=False)
    from pv_hochlauf.pipeline.fitting import compute_saturation
    c_hi_used = compute_saturation(target, float(valid[target]["kW_kum"].iloc[-1]), metadata_df)[1]
    meta = {"model_weights": {m: round(w, 4) for m, w in weights[target].items()},
            "n_similar": prob[target]["n_similar"], "last_MWp": round(hist_last, 2),
            "C_hi_MWp": round(c_hi_used / 1000, 2), "C_hi_quelle": c_hi_source}
    import json
    (cfg.OUT_CSV / f"meta_{target}.json").write_text(json.dumps(meta, indent=1))
    print(f"\nBand exportiert: {out}")
    print(f"\nLaufzeit: {time.time() - t0:.0f}s")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", default="05358024", help="AGS Zielgemeinde (Default Jülich)")
    p.add_argument("--bundesland", default="Nordrhein-Westfalen", help="Referenzpool (None=DE)")
    p.add_argument("--full", action="store_true", help="volle (langsame) DE-Parameter statt fast")
    p.add_argument("--saturation", choices=("infdb", "builda", "default"), default="infdb",
                   help="Quelle der Sättigung C_hi der Zielgemeinde (Standard: infdb)")
    p.add_argument("--infdb-dsn", default="postgresql://infdb_user:infdb@127.0.0.1:54338/infdb")
    args = p.parse_args()
    bl = None if args.bundesland.lower() in ("none", "de", "deutschland") else args.bundesland
    run(args.target, bl, fast=not args.full, saturation=args.saturation, infdb_dsn=args.infdb_dsn)


if __name__ == "__main__":
    main()
