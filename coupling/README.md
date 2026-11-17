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
    --ags 05374040 --out /tmp/ap2_scenarios.json \
    --per-building /tmp/reichshof_referenz2040.csv
uv run python ~/coding/simuflex/hochlaufszenarien/coupling/export_fillmap.py \
    --scenarios /tmp/ap2_scenarios.json \
    --out ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_fillmap.json
```
Voraussetzung: lokale InfDB auf develop (Port 54338, siehe `hochlauf/ap3_1_hochlaufszenarien/infdb_local_setup.md`) mit `basedata`/`ro_heat` der AGS und dem Solarkataster
(InfDB-Quelle `solarkataster-nrw`, übergangsweise `db/import_solarkataster.py`), AP 2 auf dem Branch `feature/pv-roof-cap`.

## Ergebnis vorher (Ersatzgrößen, Dach-Deckel mit Faktor 0,4; überholt)
Alle Band-Ziele getroffen, aber mit `alpha` ab 2035 (0,3 → 0,7 bis 2050) und 3.204 Gebäuden 2050, weil die
Ersatzgrößen (Ø 6,5 kWp) zu klein waren.

## Stand 2026-11-17: Solarkataster + MaStR-Größen
Mit Dachpotenzial aus dem Solarkataster NRW und Anlagengrößen aus dem MaStR (Ø 9,1 kWp statt Ersatzgrößen
Ø 6,5 kWp) trifft schon die KfW-2025-Struktur den Istwert 2025 (9,3 MWp bei `total` 0,163 ≈ KfW 0,16).
Die Struktur-Angleichung wird erst spät nötig: referenz 2050 `alpha` 0,2, ambitioniert ab 2040 (0,1 → 0,4).
referenz 2050: 2.467 Gebäude für 22,5 MWp (vorher 3.204). PV-Anteil referenz 2025→2050: EFH-Eigentümer
35→79 %, EFH-Mieter 10→27 %, MFH 8→26 %. Keine PV auf Dächern ohne Eignung, keine Anlage über ihrem Dach.
Karte: `notebooks/fillmap/index.html` (veröffentlicht als Artefakt, Daten `notebooks/data/reichshof_fillmap.json`).
