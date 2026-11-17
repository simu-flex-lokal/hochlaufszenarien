# coupling — AP 3.1 → AP 2 Verteilung

Verbindet das AP-3.1-Kapazitätsband mit dem **ObjectTypeGenerator** (AP 2) und verteilt die PV
realistisch auf die Gebäude. Hängt an AP 2 → **aus dessen venv ausführen**, nicht aus dem
Modellkern dieses Repos.

## Bausteine
- **Dachpotenzial je Gebäude (InfDB):** Solarkataster NRW (`db/import_solarkataster.py`), sonst
  LoD2-Dachfläche × 0,4 × 0,205 kWp/m². Dieselbe Regel nutzt AP 3.1 für `C_hi`.
- **Aufs Dach legen (in AP 2, Branch `feature/pv-roof-cap`):** Anlagengrößen aus der MaStR-Verteilung
  (`mastr/mastr_pv_kwp.csv`, erzeugt mit `mastr/derive_pv_kwp.py`), nach Größenklassen auf das Dachpotenzial
  gelegt; was auf kleine Dächer nicht passt, geht auf große. Gebäude ohne geeignetes Dach bekommen keine PV.
- **Struktur-Konvergenz (hier, `structure.py`):** die KfW-2025-Querschnittsstruktur (Haustyp×Eigentum,
  Gemeindetyp) wird über `alpha` Richtung gleichmäßig gemischt. `alpha` wird **nicht gesetzt**, sondern
  in `distribute.py` als die *minimal nötige* Angleichung bestimmt, um das MWp-Ziel real unterzubringen
  — ein Ergebnis, keine Annahme.

## Ausführen
```bash
cd ~/coding/simuflex/hochlauf/objekttypegenerator        # AP-2-venv
uv run python ~/coding/simuflex/hochlaufszenarien/coupling/distribute.py \
    --band ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_band.csv \
    --ags 05374040 --out ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_ap2_scenarios.json \
    --per-building /tmp/reichshof_referenz2040.csv
uv run python ~/coding/simuflex/hochlaufszenarien/coupling/export_fillmap.py \
    --scenarios ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_ap2_scenarios.json \
    --out ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_fillmap.json
```
Voraussetzung: lokale InfDB auf develop (Port 54338, siehe `hochlauf/ap3_1_hochlaufszenarien/infdb_local_setup.md`) mit `basedata`/`ro_heat` der AGS und dem Solarkataster
(InfDB-Quelle `solarkataster-nrw`, übergangsweise `db/import_solarkataster.py`), AP 2 auf dem Branch `feature/pv-roof-cap`.

## Ergebnis vorher (Ersatzgrößen, Dach-Deckel mit Faktor 0,4; überholt)
Alle Band-Ziele getroffen, aber mit `alpha` ab 2035 (0,3 → 0,7 bis 2050) und 3.204 Gebäuden 2050, weil die
Ersatzgrößen (Ø 6,5 kWp) zu klein waren.

## Stand 2026-11-17 (InfDB develop): Ergebnis Reichshof
Gebäudebasis: InfDB `develop` mit 6.280 bewohnten Wohngebäuden (auf `main` fehlten Gebäude aus mehreren
Gebäudeteilen, 4.185). Zensus-2022-Abgleich im 1-km-Gitter: +5 % (Wipperfürth −0,5 %), siehe
`db/check_zensus_gebaeude.py`. Dachpotenzial C_hi 91,9 MWp (Solarkataster), 261 Gebäude ohne geeignetes Dach.

- **2025:** Die KfW-Struktur (`total` 0,16) ergäbe 1.645 PV-Gebäude und 15,1 MWp, der Istwert ist 9,4 MWp. Reichshof
  liegt unter dem Bundesschnitt: MaStR zählt 955 Haushalts-Dachanlagen ≤ 30 kW (Stand 31.03.2025; 1.104 bis zum
  MaStR-Abzug). Kalibriert: `total` 0,102 → 1.035 PV-Gebäude, 9,4 MWp, Ø 9,1 kWp. Anzahl und Leistung passen
  damit beide zum MaStR. Der Batterie-Anteil sinkt mit (Anteil an den PV-Gebäuden wie KfW).
- **Bis 2050:** alle Band-Ziele mit `alpha` 0, also ohne Struktur-Angleichung. `total` referenz 0,102 → 0,241;
  referenz 2050: 2.448 Gebäude, 22,5 MWp.
- PV-Anteil referenz 2025 → 2050: EFH-Eigentümer 23 → 53 %, EFH-Mieter 4 → 13 %, MFH 6 → 14 %.
- Keine PV auf Dächern ohne Eignung, keine Anlage über ihrem Dach. Kalibrierung:
  `notebooks/data/reichshof_ap2_scenarios.json`, Karte: `notebooks/fillmap/index.html`.

## Stand 2026-11-17 auf InfDB main (überholt: 4.185 statt 6.280 Wohngebäude)
Mit Dachpotenzial aus dem Solarkataster NRW und Anlagengrößen aus dem MaStR (Ø 9,1 kWp statt Ersatzgrößen
Ø 6,5 kWp) trifft schon die KfW-2025-Struktur den Istwert 2025 (9,3 MWp bei `total` 0,163 ≈ KfW 0,16).
Die Struktur-Angleichung wird erst spät nötig: referenz 2050 `alpha` 0,2, ambitioniert ab 2040 (0,1 → 0,4).
referenz 2050: 2.467 Gebäude für 22,5 MWp (vorher 3.204). PV-Anteil referenz 2025→2050: EFH-Eigentümer
35→79 %, EFH-Mieter 10→27 %, MFH 8→26 %. Keine PV auf Dächern ohne Eignung, keine Anlage über ihrem Dach.
Karte: `notebooks/fillmap/index.html` (veröffentlicht als Artefakt, Daten `notebooks/data/reichshof_fillmap.json`).
