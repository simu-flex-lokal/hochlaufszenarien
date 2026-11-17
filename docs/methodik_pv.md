# Methodik — Photovoltaik (PV)

Konkretisierung des [Frameworks](00_framework.md) für Aufdach-PV auf Einfamilienhäusern.
Kern-Technologie. Referenzen: PV-A1…A5, PV-C1…C4, PV-B1…B7, M1 (siehe
[../literatur.md](../literatur.md), Abschnitt 3.1 inkl. Synthese).

**Empfohlener Ansatz (aus Literatursynthese):** Potential = NRW-Solarkataster direkt konsumieren
(+ Aufbauten-/Eignungskorrektur); Zeit = Bass/logistisch an MaStR-Historie, Geschwindigkeit an
Wirtschaftlichkeit/§14a gekoppelt; Raum = Spatial-Durbin-artiger Adoptionsscore mit
Nachbarschafts-Spillover.

> **Aktualisierung (2026-10, maßgeblich für PV):** Die Zeitkomponente ist jetzt das **Zielonka-Ensemble**
> ([methodik_umstellung_zielonka.md](../methodik_umstellung_zielonka.md)) — fittet 12 Modelle an die reale
> MaStR-Bestandshistorie je Gemeinde; **Anzahl und Leistung kommen damit empirisch** (enthalten reale,
> auch suboptimale Adopter). Zwei Festlegungen weichen vom obigen Erstansatz ab:
> - **Potential/Sättigung = aggregiertes Dachpotenzial `C_hi`** (lockere Obergrenze `MWp ≤ C_hi`),
>   seit 2026-11 aus der **InfDB** statt BUILDA: Σ über die bewohnten Wohngebäude der installierbaren
>   Leistung laut **Solarkataster NRW** (LANUK; Laserscan, Verschattung, Modulbelegung; per ALKIS-ID =
>   InfDB-`objectid` verknüpft, `db/import_solarkataster.py`), ohne Kataster LoD2-Dachfläche × 0,4 ×
>   0,205 kWp/m² (`io/infdb_saturation.py`) — dieselbe Regel wie das Dachpotenzial je Gebäude in AP 2. Grund: eine Datenbasis für
>   AP 2, AP 3.1 und die Netzsimulation (pylovo baut die Netze aus denselben InfDB-Gebäuden).
>   **nicht** als Per-Gebäude-Eignungsfilter. Das Solarkataster wird **nicht** als Eignungs-/Adoptionsfaktor
>   konsumiert (keine Datengrundlage für die Kalibrierung Ertrag→Adoption; wäre eine grobe Annahme).
> - **Keine Per-Gebäude-Eignungsgewichtung** im Score (kein Spatial-Durbin, kein Nachbarschafts-Spillover,
>   kein Ausrichtungs-/Verschattungsgewicht) — mangels Datengrundlage bewusst weggelassen. Die
>   Per-Gebäude-Zuordnung besitzt AP 2 (KfW-Struktur); AP 3.1 liefert nur Niveau (Anzahl + MWp) + `C_hi`.
>   Dachqualität (Ertrag Nord-/Schattendach) ist ein späteres, datenabhängiges **Profilthema**, kein
>   Adoptionskriterium. Begründung + Abwägung: [ENTSCHEIDUNGEN.md](../ENTSCHEIDUNGEN.md) (2026-10-22),
>   [03_integration.md](../03_integration.md) §3a.2. Die Abschnitte 2–4 unten beschreiben den Erstansatz.

## 1. Objektdefinition & Kenngrößen

- Objekt: Aufdach-PV-Anlage eines EFH.
- Kenngrößen: installierte Leistung `kWp` (ø EFH-Anlage), Modulfläche, Ausrichtung/Neigung.
- Ergebnisgröße: Anzahl PV-EFH je Strang/Stützjahr + Summe `kWp`.

## 2. Komponente A — Theoretisches Potential

- **Bestandsbasis:** alle EFH im Strang mit nutzbarer Dachfläche.
- **Datenquelle bevorzugt:** dachscharfes Ertragspotential direkt aus dem **Solarkataster NRW
  (LANUV)** konsumieren; LoD2 (Geobasis NRW) nur für Geometrie/Zuordnung. *Nicht* neu rechnen,
  wo das Kataster bereits ausgewertet vorliegt (PV-A2). Fallback bei Lücken: GIS-Eignungs­workflow
  + statistische Extrapolation (PV-A4).
- **Aufbauten-/Eignungskorrektur (PV-A3):** LoD2/kataster-basierte Potentiale ohne Dachaufbauten
  (Schornsteine, Gauben, Verschattung) **überschätzen ~20 %** → Eignungs-/Verfügbarkeitsfaktor
  ansetzen.
- **`N_PV,s`:** Zahl geeigneter EFH (Dachpotential über Mindest-kWp-Schwelle).
- **`P_max`:** hoher Sättigungsanteil unter geeigneten EFH (T45 sieht nahezu Vollausschöpfung
  wirtschaftlicher Dachpotentiale bis 2045). Größenordnung gegen Kosten-Potential-Kurven PV-A1
  plausibilisieren.
- **`P(t₀)`:** aktueller PV-Bestand je Strang aus **Marktstammdatenregister (MaStR)** (georeferenziert).

## 3. Komponente B — Räumliche Zuordnung

Vorbild: **Spatial-Durbin-Determinanten (PV-B1, NL, EFH-relevant)** — direkte + Spillover-Effekte.

- Score `w_i` je EFH aus zwei Blöcken:
  - *technisch:* nutzbare Dachfläche (↑), Südausrichtung/geringe Verschattung (↑), Ertrag kWh/kWp (↑).
  - *sozioökonomisch (PV-B1):* Einkommens-/Immobilienwert-Proxy (↑), Bebauungsdichte, Haushaltstyp.
- **Nachbarschafts-Spillover-Term** (PV-B2, PV-B3, PV-B4): `w_i` steigt mit Adoptionen in der
  Umgebung → räumliche Cluster; passiver (Sichtbarkeit) und aktiver (soziale Interaktion) Effekt.
- Zuordnung: rank-and-fill nach `w_i` bis `P(t)` (bzw. probabilistische Ziehung für Ensembles).
- ABM (PV-B5, PV-B6) nur für Sensitivitätsanalysen, nicht als Basisverfahren.

## 4. Komponente C — Zeitliche Entwicklung

- Kurventyp: **Bass/logistisch**, kalibriert an MaStR-**Zubauhistorie** (Zeitreihe installierter
  EFH-PV) — Historie reicht aus, „Borrowing" (PV-C3) nicht nötig.
- **Wirtschaftlichkeitskopplung (Kernbefund PV-C1, PV-C2):** Diffusion ist primär profitabilitäts-
  und regulierungsgetrieben. Diffusionsgeschwindigkeit (`r`/`t_m` bzw. `p`/`q`) daher an
  Payback/Einspeisevergütung und §14a-Anreize koppeln, nicht als reinen Zeittrend.
- Anker: T45/NEP-Zielkorridor für PV-Aufdach bis 2045.
- Downscaling regionale Kurve → Strang über Potentialanteil (Komponente A).

## 5. Datenbedarf

| Größe | Quelle |
|---|---|
| Dachflächen/-ertrag | Solarkataster NRW (LANUV), LoD2 Geobasis NRW |
| PV-Bestand & Zubauhistorie | Marktstammdatenregister (MaStR), via `open-mastr` |
| Gebäudebestand (gebäudescharf) | InfDB `basedata` (LoD2-DE, Zensus 2022); früher ETHOS.BUILDA |
| Zielpfad `P_max`/Stützwerte | Langfristszenarien T45, NEP |

## 6. Annahmen & offene Punkte

- Ø-Anlagengröße EFH festlegen (kWp) — aus MaStR-Verteilung ableiten.
- Umgang mit Bestandsanlagen/Repowering im Zeithorizont bis 2045.
- Aufbauten-/Eignungsfaktor (~20 %, PV-A3) regional kalibrieren bzw. aus Kataster-Detailgrad ableiten.
- Funktionale Kopplung Diffusionstempo ↔ Wirtschaftlichkeit/§14a konkretisieren (PV-C1/PV-C2).
- Peer-Effekt-Stärke kalibrieren (PV-B1/PV-B4) oder als Sensitivität führen.

## 7. Plausibilisierung

- `n_PV,s(t) ≤ N_PV,s`; Monotonie steigend.
- Summe kWp je Region ≈ T45/NEP-Korridor.
- Abgleich MaStR-Ist-Bestand im Basisjahr.
