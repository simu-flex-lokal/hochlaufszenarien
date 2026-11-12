# coupling — AP 3.1 → AP 2 Verteilung

Verbindet das AP-3.1-Kapazitätsband mit dem **ObjectTypeGenerator** (AP 2) und verteilt die PV
realistisch auf die Gebäude. Hängt an AP 2 → **aus dessen venv ausführen**, nicht aus dem
Modellkern dieses Repos.

## Zwei Bausteine
- **Dach-Deckel (in AP 2):** PV je Gebäude ≤ Dachpotenzial. Eigene Änderung im objecttypegenerator
  (Branch `feature/pv-roof-cap`): optionale Spalte `roof_area_m2`, Cap in `size_pv`.
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
```
Voraussetzung: lokale InfDB (Port 54328) mit `basedata`/`ro_heat`/`building_surface_area` der AGS,
AP 2 auf dem Branch `feature/pv-roof-cap`.

## Ergebnis (Reichshof, Validierung)
Alle Band-Ziele werden getroffen; `alpha` steigt plausibel über die Jahre (referenz 2035→0,3 …
2050→0,7). Der Füllpfad wandert zu Mieter-EFH/MFH: PV-Anteil referenz 2025→2050 EFH-Eigentümer
49→89 %, EFH-Mieter 13→56 %, MFH 11→56 %. Keine Anlage über ihrem Dach.
