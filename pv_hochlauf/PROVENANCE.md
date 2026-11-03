# Herkunft & Status

Dieser Code wurde aus dem **Praxisprojekt von Jan** (`praxisprojekt-jan/`, NOWUM-Energy)
übernommen — mit Zustimmung, zur Nachnutzung als **methodischer Kern** der AP-3.1-Hochlaufszenarien.

**Methodik:** werkgetreue Umsetzung von **Zielonka et al. (2023)**,
[*Probabilistic projections of granular energy technology diffusion at subnational level*](https://doi.org/10.1093/pnasnexus/pgad321),
PNAS Nexus — 4-Schritte-Pipeline:
1. deterministischer Fit von 12 Wachstumsmodellen (6 S-Kurven + 6 Bi-S-Kurven), Sättigung `C_hi` aus ETHOS.BUILDA-Dachflächen;
2. probabilistisches Band aus der Streuung ähnlicher Gemeinden (Peer-Similarity);
3. Walk-Forward-**Hindcasting** mit MAPE + **WIS** ([Bracher et al. 2021](https://doi.org/10.1371/journal.pcbi.1008618)), Gewichte ∝ 1/WIS²;
4. gewichtetes Ensemble → Quantilband + Szenariopfade.

**Literatur-Validierung** (OpenAlex/Websuche, 2026-10): SOTA bestätigt — Zielonka 2023 (PNAS Nexus, aktiv
rezipiert inkl. 2026er „policy-driven S-curves"-Strang), WIS = Forecast-Hub-Standard, Ensemble/Backtesting =
Forecasting-Best-Practice. Caveats dokumentiert in
[`methodik_umstellung_zielonka.md`](../../ap3_1_hochlaufszenarien/methodik_umstellung_zielonka.md).

## Status: übernommen, noch NICHT integriert

Der Code liegt hier zunächst **unverändert** (Attribution, Nachvollziehbarkeit). Er läuft noch als
eigenständiges Paket (eigene `config.py`-Pfade, `pyproject_jan_original.toml`). Die Integration in
unsere Pipeline (Anschluss an die SQLite-`historie`/MaStR statt eigenem Pickle-Loader; `C_hi` →
unser `potenzial`/`p_max`; Output → AP-2-Rand) ist **Phase 1** des Übernahmeplans — siehe
`ap3_1_hochlaufszenarien/methodik_umstellung_zielonka.md` und `ENTSCHEIDUNGEN.md`.

Die Originaldaten (MaStR-Pickle ~900 MB, Caches, Outputs) sind **nicht** übernommen — die Historie
kommt bei uns aus der DB (`import_mastr.py`), das BUILDA-Potenzial über den `ethos-builda-client`.
