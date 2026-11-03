"""
pv_hochlauf_main.py — Ausführendes Hauptskript.

Führt die vollständige 4-Schritte-Pipeline nach Zielonka et al. (2023) aus:

  Schritt 1 : Deterministische Projektionen (DE → NLS, parallel)
  Schritt 2 : Probabilistische Projektionen (ähnliche Gemeinden)
  Schritt 3 : Hindcasting → Modellgewichte (MAPE + WIS)
  Schritt 4 : Gewichtetes Ensemble + Szenariopfade
              Ersatzprojektionen für ausgeschlossene Gemeinden

Konfiguration: pv_hochlauf/core/config.py
  → TEST_MODE, TARGET_GEMEINDEN, FORCE_RECOMPUTE etc.

Datenquelle: Datenbankverbindung in pv_hochlauf/io/database.py
  → Verbindungsparameter dort eintragen
  → Alternativ: load_local_data() für lokale Datei
"""

import pandas as pd
import sys
from pathlib import Path


# --- Konfiguration (zuerst importieren, setzt Ausgabeverzeichnisse) ---
from pv_hochlauf.core.config import (
    PROJ_END, QUANTILES, N_SCENARIO_PATHS,
    FORCE_RECOMPUTE, TEST_MODE, TEST_MAX_GEMEINDEN,
    TARGET_GEMEINDEN,
    SAVE_DET_PROJ,
    USE_BUILDA_SATURATION,
    BASE_DIR
)

# --- Daten-IO ---
from pv_hochlauf.io.saturation import (
    fetch_builda_saturation_bulk, build_metadata_df, saturation_summary,
)
from pv_hochlauf.io.database import (
    load_mastr_data, prepare_timeseries, 
    filter_timeseries,
)
from pv_hochlauf.io.cache import (
    save_det_proj, load_det_proj, save_prob_proj, load_prob_proj, save_weights_scores, load_weights_scores
)
from pv_hochlauf.io.export import export_gemeinde_csv, export_national_csv

# --- Pipeline ---
from pv_hochlauf.pipeline.fitting      import step1_deterministic_parallel
from pv_hochlauf.pipeline.probabilistic import step2_probabilistic
from pv_hochlauf.pipeline.hindcasting  import step3_hindcasting
from pv_hochlauf.pipeline.ensemble     import (
    step4_ensemble, compute_excluded_ensemble
)

# --- Visualisierung ---
from pv_hochlauf.visualization.plots import (
    plot_fit_validation, plot_hochlauf_gemeinde,
    plot_hindcast_heatmap
)


def main():
    print("=" * 62)
    print("PV-Hochlauf nach Zielonka et al. (2023)")
    print("Methodik: 4-Schritte-Pipeline, Gemeindeebene, 12 S-Kurven")
    if TEST_MODE:
        print("*** TEST-MODUS AKTIV (TEST_MODE=True in config.py) ***")
    print("=" * 62)

    # ----------------------------------------------------------------
    # DATEN LADEN
    # Variante A: Datenbank (Verbindungsparameter in io/database.py)
    # Variante B: Lokale Datei (schneller)
    # ----------------------------------------------------------------
    # df_raw = load_mastr_data()                          # Variante A
    df_raw = pd.read_pickle(BASE_DIR / "Daten" / "mastr_data.pkl")     # Variante B
    cities_dict = {
    ags: {
        "Gemeinde": group["Gemeinde"].iloc[0],
        "Postleitzahl": [str(plz) for plz in group["Postleitzahl"].dropna().unique()]
        }
        for ags, group in df_raw.groupby("Gemeindeschluessel")
    }

    print("\nDatenaufbereitung ...")
    gemeinde_ts_all = prepare_timeseries(df_raw)

    # ----------------------------------------------------------------
    # ZEITREIHENFILTER
    # ----------------------------------------------------------------
    gemeinde_ts_valid, gemeinde_ts_excl = filter_timeseries(
        gemeinde_ts_all, metric="kW_kum")

    # Zielgemeinden prüfen (vor Schritt 1)
    if TARGET_GEMEINDEN is not None:
        missing_from_data = [g for g in TARGET_GEMEINDEN
                             if g not in gemeinde_ts_all]
        if missing_from_data:
            raise ValueError(
                f"Zielgemeinden nicht in MaStR-Daten: {missing_from_data}\n"
                f"Bitte Gemeindeschluessel prüfen."
            )
        missing_from_valid = [g for g in TARGET_GEMEINDEN
                              if g not in gemeinde_ts_valid]
        if missing_from_valid:
            print(f"  HINWEIS: Folgende Zielgemeinden sind ausgeschlossen "
                  f"(ungültige Zeitreihe) und erhalten Ersatzprojektion:")
            for g in missing_from_valid:
                print(f"    → {gemeinde_ts_all[gemeinde_ts_all['Gemeindeschluessel'] == g]['Gemeinde']}")
        target_valid = [g for g in TARGET_GEMEINDEN if g in gemeinde_ts_valid]
        target_excl  = [g for g in TARGET_GEMEINDEN if g not in gemeinde_ts_valid]
    else:
        target_valid = None
        target_excl  = []

    # TEST-MODUS: Auf Top-N Gemeinden beschränken
    if TEST_MODE and TEST_MAX_GEMEINDEN is not None:
        top_n = sorted(
            gemeinde_ts_valid.keys(),
            key=lambda g: gemeinde_ts_valid[g]["kW_kum"].iloc[-1],
            reverse=True,
        )[:TEST_MAX_GEMEINDEN]
        gemeinde_ts_valid = {g: gemeinde_ts_valid[g] for g in top_n}
        print(f"  TEST-MODUS: {len(gemeinde_ts_valid)} Gemeinden "
              f"(Top-{TEST_MAX_GEMEINDEN} nach Leistung)")

    # ----------------------------------------------------------------
    # SCHRITT 1: Deterministische Projektionen (mit Cache)
    # ----------------------------------------------------------------
    print("\nSchritt 1: Deterministische Projektionen ...")
    det_proj = None
    if not FORCE_RECOMPUTE:
        det_proj = load_det_proj()

    metadata_df = None
    sat_data: dict = {}  # Sättigungspotenziale je Gemeinde
    if USE_BUILDA_SATURATION:
        print("\nSättigungspotenziale via ETHOS.BUILDA ...")
        # Abfrage der Gebäudedaten über den Ethos-Builda-Client und aggregierte Zwischenspeicherung
        # Wenn die Daten für eine Gemeinde bereits Abgefragt und gespeichert wurden, werden sie aus
        # dem Cache geladen
        sat_data = fetch_builda_saturation_bulk(cities_dict)
        metadata_df = build_metadata_df(sat_data)
        saturation_summary(metadata_df)

    if det_proj is None:
        det_proj = step1_deterministic_parallel(
            gemeinde_ts_valid, metric="kW_kum", metadata_df=metadata_df, proj_end=PROJ_END)
        if SAVE_DET_PROJ:
            save_det_proj(det_proj)

   # ----------------------------------------------------------------
    # SCHRITT 2: Probabilistische Projektionen (mit Cache)
    # ----------------------------------------------------------------
    print("\nSchritt 2: Probabilistische Projektionen ...")

    # Cache laden und prüfen welche Zielgemeinden bereits vorhanden sind
    cached_prob = {}
    if not FORCE_RECOMPUTE:
        cached_prob = load_prob_proj() or {}
    
    targets_for_step2 = (
        [g for g in target_valid if g not in cached_prob]
        if target_valid is not None
        else [g for g in det_proj if g not in cached_prob]
    )

    if targets_for_step2:
        print(f"  {len(targets_for_step2)} Gemeinden neu berechnen, "
            f"{len(cached_prob)} aus Cache")
        prob_proj_new = step2_probabilistic(
            det_proj, target_gemeinden=targets_for_step2)
        save_prob_proj(prob_proj_new)
        # Zusammenführen: Cache + neu berechnete
        prob_proj = {**cached_prob, **prob_proj_new}
        # Nur Zielgemeinden weiterverwenden
        if target_valid is not None:
            prob_proj = {g: prob_proj[g] for g in target_valid if g in prob_proj}
    else:
        print(f"  Alle Gemeinden aus Cache ({len(cached_prob)})")
        prob_proj = cached_prob
        if target_valid is not None:
            prob_proj = {g: prob_proj[g] for g in target_valid if g in prob_proj}

    # ----------------------------------------------------------------
    # SCHRITT 3: Hindcasting (mit Cache)
    # ----------------------------------------------------------------
    print("\nSchritt 3: Hindcasting ...")

    cached_weights = {}
    cached_scores  = {}
    if not FORCE_RECOMPUTE:
        cached_ws = load_weights_scores() or {"weights": {}, "scores": {}}
        cached_weights = cached_ws["weights"]
        cached_scores  = cached_ws["scores"]

    targets_for_step3 = (
        [g for g in target_valid if g not in cached_weights]
        if target_valid is not None
        else [g for g in gemeinde_ts_valid if g not in cached_weights]
    )

    if targets_for_step3:
        print(f"  {len(targets_for_step3)} Gemeinden neu berechnen, "
            f"{len(cached_weights)} aus Cache")
        weights_new, scores_new = step3_hindcasting(
            det_proj,
            target_gemeinden=targets_for_step3
        )
        save_weights_scores(weights_new, scores_new)
        # Zusammenführen: Cache + neu berechnete
        weights = {**cached_weights, **weights_new}
        scores  = {**cached_scores,  **scores_new}
        # Nur Zielgemeinden weiterverwenden
        if target_valid is not None:
            weights = {g: weights[g] for g in target_valid if g in weights}
            scores  = {g: scores[g]  for g in target_valid if g in scores}
    else:
        print(f"  Alle Gemeinden aus Cache ({len(cached_weights)})")
        weights = cached_weights
        scores  = cached_scores
        if target_valid is not None:
            weights = {g: weights[g] for g in target_valid if g in weights}
            scores  = {g: scores[g]  for g in target_valid if g in scores}

    # ----------------------------------------------------------------
    # SCHRITT 4: Gewichtetes Ensemble (valide Gemeinden)
    # ----------------------------------------------------------------
    print("\nSchritt 4: Ensemble + Szenariopfade ...")
    ensemble = step4_ensemble(prob_proj, weights)

    # ----------------------------------------------------------------
    # SCHRITT 4b: Ersatzprojektionen für ausgeschlossene Gemeinden
    # Nach Zielonka Supp. A.5 / Tabelle S1e:
    #   Durchschnittliche Gewichte + Wachstumsrate aller validen Gemeinden
    # ----------------------------------------------------------------
    print("\nErsatzprojektionen (ausgeschlossene Gemeinden) ...")
    ensemble_excl = compute_excluded_ensemble(
        gemeinde_ts_excl=gemeinde_ts_excl,
        prob_proj_valid=prob_proj,
        weights_valid=weights,
    )

    # Alle Gemeinden zusammenführen
    ensemble_full = {**ensemble, **ensemble_excl}
    print(f"  Ensemble gesamt: {len(ensemble_full):,} Gemeinden "
          f"({len(ensemble)} valide + {len(ensemble_excl)} mit Ersatz)")

    # ----------------------------------------------------------------
    # PLOTS & CSV-EXPORT
    # ----------------------------------------------------------------
    print("\nPlots und CSV-Export ...")

    # Gemeinde-Ausgabe: Zielgemeinden (falls angegeben) oder Top-5
    if TARGET_GEMEINDEN is not None:
        plot_gemeinden = TARGET_GEMEINDEN
    else:
        plot_gemeinden = sorted(
            gemeinde_ts_valid.keys(),
            key=lambda g: gemeinde_ts_valid[g]["kW_kum"].iloc[-1],
            reverse=True,
        )[:5]

    for gemeinde in plot_gemeinden:
        print(f"\n  {cities_dict[gemeinde]['Gemeinde']}:")
        if gemeinde in ensemble:
            # Valide Gemeinde: alle Plots
            C_hi = sat_data.get(gemeinde) or det_proj[gemeinde]["C_hi"]
            plot_fit_validation(gemeinde, det_proj)
            plot_hochlauf_gemeinde(gemeinde, ensemble, C_hi)
            plot_hindcast_heatmap(scores[gemeinde], weights[gemeinde], gemeinde)
            export_gemeinde_csv(gemeinde, ensemble, cities_dict)
        elif gemeinde in ensemble_excl:
            # Ausgeschlossene Zielgemeinde: nur Hochlauf-Plot
            print(f"    (Ersatzprojektion — kein individueller Fit)")
            plot_hochlauf_gemeinde(gemeinde, ensemble_excl)
            export_gemeinde_csv(gemeinde, ensemble_excl, cities_dict)
        else:
            print(f"    WARNUNG: {gemeinde} nicht in Ergebnissen gefunden.")

    from pv_hochlauf.core.config import OUT_PLOTS, OUT_CSV
    n_plots = len(list(OUT_PLOTS.glob("*.png")))
    n_csvs  = len(list(OUT_CSV.glob("*.csv")))
    print(f"\n{'=' * 62}")
    print(f"✓ Fertig. {n_plots} Plots, {n_csvs} CSVs in ./outputs/")


if __name__ == "__main__":
    main()