# Methodik-Umstellung: Zielonka-Ensemble als Kern (Übernahme aus Jans Praxisprojekt)

Strategischer Schwenk (2026-10): **methodische Tiefe vor Technologie-Breite und Paket-Ästhetik.** Ziel
von AP 3.1 ist nicht eine schöne Bibliothek, sondern **sehr gute, belastbare Hochlaufszenarien**, die
mit AP 2 (Objekttypen, Phillip) und AP 3.2 (Netz) verbunden werden. Dazu übernehmen wir die
Zielonka-2023-Pipeline aus Jans Praxisprojekt als **methodischen Kern** der Zeitkomponente.

## 1. Literatur-Validierung (adversarial geprüft, bestätigt)

Vor dem Umstieg geprüft (OpenAlex + Websuche), weil wir nichts methodisch Weiches mehr wollen:

- **SOTA, peer-reviewed, aktiv weiterentwickelt:** Zielonka 2023 ([PNAS Nexus](https://doi.org/10.1093/pnasnexus/pgad321),
  33 Zit.), Zielonka 2025 ([iScience](https://doi.org/10.1016/j.isci.2025.111825), 19 Zit.); 2026er-Rezeption
  u.a. „Rethinking S-curves for policy-driven energy technologies" → **unsere geplante normative/§14a-Schicht
  ist selbst ein aktiver Forschungsstrang auf Zielonka aufbauend.**
- **Etablierte Bausteine:** Ensemble/Modellkombination schlägt Einzelmodelle (Petropoulos et al. 2022,
  *Forecasting: theory and practice*); **WIS** = [Bracher et al. 2021](https://doi.org/10.1371/journal.pcbi.1008618),
  Standard des COVID-/CDC-Forecast-Hubs; Hindcasting + gebundene Sättigung = Best Practice.

**Caveats (zu respektieren, nicht zu ignorieren):**
1. Kein Einzelmodell ist immer das beste; **einfachere Modelle prognostizieren oft besser**, datenbasiert
   **fixierte Sättigung** ist ein schwer zu schlagender Benchmark → Hindcast-Gewichtung schwächt schlecht
   backtestende (komplexe) Modelle ab; BUILDA-gebundene `C_hi` ist methodisch sauber. Den flexibelsten
   Modellen (Richards-5p, Bi-S) **nicht blind** trauen.
2. **Formative-Phase-Overfitting**: pre-wendepunkt-Technologien sind überzuversichtlich zu fitten. PV (DE,
   2000–2024, oft über Wendepunkt) ok; **WP/EV riskanter** (dünn/national, pre-inflection).
3. S-Kurven = empirische Regelmäßigkeit, **kein Kausalgesetz** → §14a nicht als Kausalinferenz überverkaufen
   (deckt sich mit RQ2-Entschärfung).

## 2. Ziel-Architektur (Re-Mapping unserer Komponenten)

| Schicht | bisher | neu |
|---|---|---|
| Daten/Provenienz | SQLite-DB, MaStR, VG250, FfE | **bleibt** (Quelle + Historie + Provenienz) |
| **A — Potential / `C_hi`** | flacher EFH-Faktor 0,80 | **BUILDA-Dachflächen-Physik** (`saturation.py`) je Gemeinde |
| **C — Diffusion** | einzelne Logistik, p_max fix | **Ensemble + Hindcast** (12 Modelle, WIS-gewichtet) → Quantilband |
| **B — Zuordnung** | rank-and-fill | **an AP 2** (IPF-Ziehung, §3a); `allocation.py` = optionaler Standalone |
| Output | deterministische Zahlen | **Gemeinde × Jahr × Szenario × Quantil** → Rand für AP 2 |

## 3. Grundsatz: zwei orthogonale Achsen (bestätigt)

Jans Modell ist **deskriptiv** (Prognose + Unsicherheit aus Historie); AP 3.1 braucht **normative**
Szenarien (T45-Anker, §14a). Beides kombinieren statt ersetzen:

- **Szenario-Achse** (normativ): setzt den *Anker* — Anteil von `C_hi`, der bis wann erreicht wird; §14a als
  Beschleunigung der Kurve (der endgültige Ort für unseren bisher fehlenden K5-Kanal).
- **Quantil-Achse** (deskriptiv): Ensemble+Peer-Band = Unsicherheit um jeden Anker.

→ **Output = Gemeinde × Jahr × Szenario × Quantil.** Reihenfolge: erst deskriptive Basis, dann normative
Schicht darüber.

## 4. Phasen-Roadmap

- **Phase 0 — Übernahme (erledigt):** Jans Quellcode nach `hochlauf_model/pv_hochlauf/` vendort (ohne Daten),
  Provenienz vermerkt. Mit Jan abgestimmt (Nachnutzung ok).
- **Phase 1 — PV deskriptiv in unsere Pipeline:** Jans Module an unsere DB andocken — Historie aus
  `historie`/MaStR statt Pickle-Loader; `C_hi` (BUILDA) → `potenzial`; `diffusion.py` ablösen. Ergebnis:
  validiertes PV-Quantilband je Gemeinde. **Behebt Review-K1/K2** (echtes Hindcasting; BUILDA-verankerte C).
- **Phase 2 — Normative Schicht:** Szenario-Anker (C_hi-Anteil / Tempo) + §14a-Beschleunigung über das Band.
- **Phase 3 — AP-2-Übergabe:** Rand-Export (Gemeinde×Jahr×Szenario×Quantil); kW↔Durchdringung/Anzahl klären.
  Jans Gemeinde-Output passt direkt als Rand (sogar mit Band).
- **Phase 4 — Multi-Tech:** WP & EV mit derselben Methodik. **Ehrlich:** Peer-Similarity braucht
  gemeindescharfe Historie (PV reich; WP/EV dünn/national) und der reine S-Kurven-Ensemble erfasst **keinen
  Konkurrenztech-Umschlag** (K4) → WP/EV brauchen die Bestands-Fluss-Schicht obendrauf.

## 5. Konsequenzen für die Positionierung

Ehrlicher Schwenk in [FORSCHUNGSLUECKE.md](FORSCHUNGSLUECKE.md): weniger „neuartiges eigenständiges Framework",
mehr **methodisch rigorose, unsicherheitsquantifizierte Multi-Tech-Hochlaufszenarien für NS-Netze, integriert
mit dem AP-2-Objektmodell**. Jans PV-Arbeit + Zielonka werden als (instituts- bzw. literatur-)Vorarbeit sauber
genannt, auf der wir aufbauen.
