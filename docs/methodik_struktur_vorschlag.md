# Vorschlag: Verteilung des PV-Zubaus auf Gebäudegruppen (ersetzt `alpha`)

Stand 2026-11-18. Vorschlag zur Entscheidung, noch nicht umgesetzt.

## 1. Problem

AP 3.1 liefert je Gemeinde und Jahr ein Band für die PV-Leistung. AP 2 verteilt PV auf Gebäude. Dafür nutzt es die
PV-Anteile der KfW-Erhebung 2025 nach Haustyp × Eigentum: EFH-Eigentümer 34 %, EFH-Mieter 9 %, MFH 6–9 %
([KfW 2025b, Tab. 4][kfw25t]).

Steigt das Band, stößt die Gruppe EFH-Eigentümer irgendwann an 100 %. Bisher löst das `alpha`
(`coupling/structure.py`): Die Gruppenanteile werden linear in Richtung „alle Gruppen gleich“ gemischt, gerade so
weit wie nötig. Der Wert von `alpha` ergibt sich aus der Kalibrierung. Die Form ist aber eine Annahme:

- **Ziel ohne Beleg:** Dass sich die Gruppen auf einen gleichen Anteil zubewegen, ist durch nichts belegt (Abschnitt 2).
- **Keine Sättigung je Gruppe:** Eigentümer-EFH werden nur durch die 100-%-Grenze gebremst, nicht durch ein
  beobachtetes Potenzial.
- **Ein Schalter für alles:** Ein einziger Parameter steuert alle Gruppen. Unterschiedliche Hürden, etwa beim Mieterstrom,
  lassen sich damit nicht abbilden.

**Anforderungen an den Ersatz.**
1. 2025 trifft er die heutige Struktur.
2. Die Summe folgt dem Band.
3. Keine Gruppe überschreitet ihr Potenzial.
4. Jede Annahme ist mit Daten oder Literatur belegt.

## 2. Was Daten und Literatur sagen

### 2.1 Zeitreihe der KfW-Erhebung: Die Gruppen nähern sich nicht an

Anteil der Haushalte mit PV auf dem Dach (vorhanden). Quellen: Methoden- und Tabellenbände
[2019][kfw19], [2020][kfw20], [2021][kfw21], [2022][kfw22], [2025][kfw25t], jeweils Tab. 4. Für 2023 und 2024 gibt es
nur Eigentümer und alle Haushalte aus den Hauptberichten [2023][kfw23] und [2024][kfw24]; die Mieterwerte sind daraus
zurückgerechnet (Mieteranteil ≈ 55 %).

| Gruppe | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| EFH/ZFH, Eigentümer | 12,8 % | 14,4 % | 12,6 % | 16,4 % | | | 34 % |
| EFH/ZFH, Mieter | 4,8 % | 7,3 % | 11,9 % | 7,1 % | | | 9 % |
| Wohnung (MFH), Eigentümer | 6,2 % | 5,3 % | 7,5 % | 5,9 % | | | 9 % |
| Wohnung (MFH), Mieter | 2,7 % | 4,5 % | 4,8 % | 4,1 % | | | 6 % |
| alle Eigentümer | 11,5 % | 12,9 % | 11,6 % | 14,6 % | 19,2 % | 25,5 % | 29 % |
| alle Mieter | 3,0 % | 4,9 % | 6,2 % | 4,5 % | ≈ 5,6 % | ≈ 5,9 % | 7 % |
| Verhältnis Eigentümer : Mieter | 3,8 | 2,6 | 1,9 | 3,2 | ≈ 3,4 | ≈ 4,3 | 4,1 |

- **Keine Annäherung:** Der Boom seit 2022 kam fast nur bei Eigentümern an. Deren Abstand zu den Mietern ist wieder
  gewachsen.
- **Unsicherheit:** Die kleinen Gruppen sind unsicher, EFH-Mieter haben nur rund 250–290 Befragte (±1,5–2 Prozentpunkte).
- **Methodenbrüche:** 2024 wurden die Vorjahreswerte neu berechnet. Seit 2025 werden Balkonkraftwerke getrennt erfasst,
  vorher waren sie teils als Dachanlage gezählt ([KfW 2025a][kfw25]). Die Mieterwerte bis 2022 sind deshalb eher zu
  hoch und ihr Anstieg eher zu niedrig.

**Folgerung:** Eine Annäherung aller Gruppen an einen gleichen Anteil, wie `alpha` sie unterstellt, ist bisher nicht
beobachtet.

### 2.2 Wie hoch die Sättigung je Gruppe liegt

- **EFH-Eigentümer:** 57 % der Eigentümer ohne PV können sich eine Anlage vorstellen ([KfW 2025a][kfw25]). Daraus folgt
  als obere Grenze 34 % + 0,57 × 66 % ≈ **72 %**.
  - In dieser Grenze stecken auch Dächer, die technisch nicht passen. Wer kein geeignetes Dach hat, verneint die Frage
    meist.
  - Die Hürden für die übrigen Eigentümer sind finanziell: 33–36 % sagen „kann ich mir nicht leisten“, 32–36 %
    „lohnt sich nicht“ ([KfW 2026][kfw26]).
- **Mieter und MFH:** Hier gibt es keine Befragung zum Potenzial. Belegt sind nur die Hürden:
  - **Vermieter rechnen künftige Erträge stark ab.** Sie bewerten einen Euro künftigen PV-Ertrags mit 0,40 €,
    Eigentümer mit 0,66 €. Das entspricht einem impliziten Zins von 18,9 % gegenüber 8,8 %. Der Aufwand für
    Mieterstromverträge frisst 40–62 % der Mieterstrom-Erlöse. Fallen diese Hürden weg, könnte sich die Zahl möglicher
    Anleger mehr als verdoppeln ([von Ditfurth & Rausch 2025][zew]).
  - **Großes technisches Potenzial, kaum genutzt.** Auf 3,1 Mio. MFH passen bis zu 60 GW, ohne
    Wohnungseigentümergemeinschaften (WEG) 42 GW. Mieterstrom gibt es erst in rund 5.000 Gebäuden. PV-Anlagen auf MFH
    sind meist 30–100 kWp groß ([Fischer & Henger 2025][ariadne]).
  - **Gemeinsame Gebäudeversorgung seit Solarpaket I** (§ 42b EnWG): Sie soll die Hürden senken. Eine Wirkung ist noch
    nicht messbar.

### 2.3 Wie andere Modelle das lösen

- **Kein etablierter Standard.** Für die Frage „wie verschiebt sich der Zubau zwischen Gebäudegruppen“ haben wir kein
  Standardverfahren gefunden.
- **Getrennte Anlegergruppen mit eigenem Markt.** Ökonometrische Modelle trennen Anlegergruppen, jede mit eigener
  Marktgröße und eigenem Entscheidungsverhalten ([von Ditfurth & Rausch 2025][zew]). Bass-Modelle auf Ebene von
  Postleitzahlen geben jedem Segment ein eigenes Langfrist-Potenzial und erklären es über den Eigentümeranteil
  ([SDG&E EPIC-2][sdge]).
- **Agentenmodelle.** Agentenbasierte Gebäudemodelle bilden Eigentümer und Mieter als Agenten ab
  ([Fraunhofer IEE AgentHomeID][iee]). Das ist detailreich, aber aufwendig und nicht offen verfügbar.
- **Durchdringung auf Gebäudeebene.** Die KfW selbst schätzt sie aus MaStR-Haushaltsanlagen je Wohngebäude mit 1–2
  Wohnungen: Ende 2023 hatten etwa 12 % PV ([KfW Fokus 457][fokus]).

### 2.4 Eigene Empirie: Gemeinde-Querschnitt nicht belastbar

**Frage:** Lässt sich aus allen Gemeinden ablesen, wie viel PV jede Gebäudegruppe hat und wie sich das über die Jahre
ändert?

**Daten:** 10.467 Gemeinden, je Gemeinde die Zahl der Gebäude je Gruppe aus dem Zensus 2022 und die MaStR-Anlagen
(Haushalt, Dach, 1–30 kW, kumuliert 2012–2025).

**Rechnung:** Je Jahr eine Regression des PV-Anteils je Gebäude auf die Anteile der Gruppen, mit und ohne Kontrolle
für Bundesland und Gemeindegröße.

**Ergebnis: nicht verwertbar.**
- MFH erhalten negative Werte (−0,03 bis −0,13).
- EFH-Mieter liegen mit Kontrollen über den Eigentümern (Faktor 1,2–2,4).
- Die Werte springen je nach Spezifikation.

**Ursache:** Der Gebäudemix einer Gemeinde hängt eng mit Ländlichkeit, Einkommen und Dachgröße zusammen
(ökologischer Fehlschluss).

**Was besser ginge:** Ein Abgleich Gebäude für Gebäude. Die öffentliche MaStR-Fassung enthält für kleine Anlagen aber
keine Adresse. Möglich wäre das mit PV-Erkennung aus Luftbildern auf LoD2-Gebäuden für NRW
([3D-PV-Locator, Mayer et al. 2022][pvloc]). Der Aufwand liegt bei grob 3–6 Wochen und ist ein eigenes Arbeitspaket.

## 3. Varianten

### A – Sättigung je Gruppe, gemeinsames Markttempo (Empfehlung)

**Idee.**
- Jede Gruppe *k* hat ein eigenes Potenzial *S_k*, also den höchsten erreichbaren PV-Anteil, und ein eigenes relatives
  Tempo *r_k*.
- Das Band bestimmt nur, wie schnell der Markt insgesamt ist: *h(t)*. Das ist ein Wert je Jahr, so gewählt, dass die
  Summe das Band trifft.
- Nähert sich eine Gruppe ihrem Potenzial, wird ihr Zubau von selbst kleiner. Der Rest des Bands geht dann auf die
  anderen Gruppen über.
- Die Verschiebung zwischen den Gruppen folgt damit aus Daten und muss nicht angenommen werden. Das ist ein
  Bass-Modell mit Segmenten, bei dem die Hazards im festen Verhältnis zueinander stehen.

**Formel.**

  p_k(t+1) = p_k(t) + (1 − e^(−r_k·h(t))) · (S_k − p_k(t)),

  wobei h(t) so gewählt ist, dass Σ_k N_k · p_k(t+1) gleich dem Ziel nach Band ist (Gebäude bzw. kWp).

- **Start:** p_k(2025) = KfW-Struktur, skaliert auf den MaStR-Istwert der Gemeinde. Das macht die Kalibrierung schon
  heute.
- **Obergrenze:** Kein p_k kann über S_k steigen.
- **Unerreichbares Band:** Liegt das Band über Σ N_k · S_k, gibt es keine Lösung. Das wird gemeldet und nicht
  stillschweigend abgeschnitten.

**Parameter und Quellen.**

| Parameter | Wert (Vorschlag) | Quelle / Herleitung |
|---|---|---|
| S EFH-Eigentümer | 0,72 | [KfW 2025a][kfw25]: 34 % + 57 % der Übrigen |
| S EFH-Mieter, MFH | 0,5 (Szenario), 0,6 bei sinkenden Hürden | keine Erhebung. Abgeleitet aus dem technischen MFH-Potenzial ohne WEG (≈ 70 % von 60 GW, [Ariadne][ariadne]) und der Zahlungsbereitschaft der Vermieter (0,40 statt 0,66, [ZEW][zew]). **Szenarioparameter** |
| r EFH-Eigentümer | 1 (Bezug) | Hazard 2022→2025 ≈ 0,13 pro Jahr |
| r EFH-Mieter, MFH | 0,12–0,15 heute, 0,4 bei sinkenden Hürden | KfW 2022→2025 je Gruppe bei S = 0,5: Hazard 0,015–0,024 pro Jahr, also 12–19 % des Eigentümer-Tempos; wegen der Balkon-Bereinigung eher Untergrenze |

**Anschluss an AP 2.** Die Kopplung gibt AP 2 je Jahr die Gruppenwahrscheinlichkeiten p_k(t) vor statt `total` und
`alpha`. Die Gemeindetyp-Achse bleibt beim Lauf einer einzelnen Gemeinde neutral. Dachausschluss und Größenzuschnitt
macht AP 2 wie bisher. Technisch reicht es, in `pv_with_structure` die Haustyp × Eigentum-Margin durch p_k(t) zu
ersetzen. Sauberer wäre eine kleine Erweiterung in AP 2: „Gruppenwahrscheinlichkeiten je Gemeinde vorgeben“.

**Passt zum Band, mit eingebauter Kontrolle.** Das Band legt die Summe fest. Wie viel davon auf jede Gruppe entfällt,
folgt aus S und r. Das nötige Markttempo h(t) dient als Kontrolle:
- Liegt h(t) weit über dem, was bisher beobachtet wurde (≈ 0,13 pro Jahr), verlangt das Band mehr, als die Gruppen
  hergeben.
- Dann passt entweder das Band nicht zu den Gruppen-Potenzialen, oder die Hürden für Mieter und MFH müssen sinken. Das
  wäre eine Szenario-Aussage.
- Optional lässt sich auch die Sättigung des Bands (C_hi) aus Σ N_k · S_k · Dachpotenzial ableiten. Dann passen beide
  Ebenen per Konstruktion zusammen.

**Stärken:**
- Jeder Parameter hat eine Quelle oder ist ausdrücklich ein Szenarioparameter.
- Gruppen sättigen einzeln.
- Hürden für Mieter und MFH (Mieterstrom, § 42b EnWG) lassen sich direkt über r und S als Szenarien abbilden.
- Übersteigt das Band die Potenziale, wird das sichtbar.

**Schwächen:**
- S für Mieter und MFH ist nicht gemessen.
- r beruht auf drei Jahren KfW-Daten mit kleinen Stichproben.
- Es sind Haushaltsanteile; für MFH ist das nur eine Näherung für den Anteil der Gebäude.

**Aufwand:** etwa 2–3 Tage (Modul, Kalibrierung, Tests, Doku).

### B – Beobachtete Struktur fortschreiben

**Idee:** Die Gruppenverhältnisse der KfW-Reihe 2019–2025 als Trend fortschreiben, gedeckelt bei 100 %.

**Bewertung:**
- Einfach.
- Der Trend zeigt aber keine Annäherung (Verhältnis Eigentümer : Mieter 3,8 → 4,1). Die Eigentümer-EFH laufen in
  Wipperfürth also früh an die Grenze, und dasselbe Problem wie mit `alpha` kehrt zurück.
- Die Daten sind verrauscht und haben Methodenbrüche.
- Bis 2050 fortzuschreiben ist nicht belastbar.

**Nicht empfohlen.**

### C – Wirtschaftliches Entscheidungsmodell je Gruppe

**Idee:** Je Gruppe die Wirtschaftlichkeit berechnen, mit eigenem Abzinsungssatz (8,8 % bzw. 18,9 %, [ZEW][zew]),
Mieterstrom-Kosten, Förderung und Strompreis. Die Anschaffung folgt einer Entscheidungsfunktion.

**Bewertung:**
- Bildet Instrumente am genauesten ab.
- Rechnet aber den Hochlauf ein zweites Mal von unten. Das konkurriert mit dem Band aus AP 3.1 und braucht
  Preisszenarien bis 2050.

**Aufwand:** etwa 2–3 Wochen.

**Sinnvoll als Ergänzung:** Mit C lassen sich die Szenariowerte von r und S für Variante A begründen, etwa: Wie stark
steigt r, wenn die Mieterstrom-Kosten halbiert werden?

## 4. Grobe Abschätzung (Variante A, Szenario referenz)

Rechnung über die Zahl der PV-Gebäude; Ziel = Band p50 / 9,1 kWp. Gruppen nach InfDB `develop`: Reichshof 4.016
EFH-Eigentümer, 596 EFH-Mieter, 1.668 MFH; Wipperfürth 3.236 / 535 / 2.033.

| PV-Anteil 2050 | EFH-Eig. | EFH-Miet. | MFH | nötiges Tempo h 2045 |
|---|---|---|---|---|
| Reichshof, heute `alpha` | 53 % | 13 % | 14 % | – |
| Reichshof, A Status quo | 55 % | 11 % | 11 % | 0,04 |
| Reichshof, A Hürden sinken | 50 % | 21 % | 20 % | 0,02 |
| Wipperfürth, heute `alpha` | 74 % | 34 % | 34 % | – |
| Wipperfürth, A Status quo | 72 % (= S) | 34 % | 37 % | **0,47** |
| Wipperfürth, A Hürden sinken | 69 % | 41 % | 40 % | 0,11 |

**Was die Abschätzung zeigt:**
- Die Anteile 2050 liegen nahe an den heutigen `alpha`-Ergebnissen. Der Unterschied liegt in der Begründung und in
  der Kontrolle.
- **Wipperfürth erreicht das Band im Status quo nur mit einem unplausiblen Tempo** (0,47 pro Jahr, das 3,6-Fache des
  bisher beobachteten). Die Eigentümer-EFH sind dann ausgeschöpft.
- `alpha` hat das verdeckt. Variante A zeigt es offen: Das obere Band in Wipperfürth setzt voraus, dass die Hürden für
  Mieter und MFH sinken.

Rechnung: `docs/methodik_struktur_abschaetzung.py` (Skizze, wird bei Umsetzung ein Modul). Gemeinde-Regression aus 2.4: `docs/methodik_struktur_gemeinde_regression.py` (läuft im ObjectTypeGenerator-venv; MaStR-Aggregat aus OEDS `mastr-2025.solar_extended`).

## 5. Offene Entscheidungen

1. **Variante A als Ersatz für `alpha`?** Empfehlung: ja.
2. **S und r für Mieter und MFH:** als Szenarioparameter mit zwei Stufen (Status quo / Hürden sinken)? Und an welche
   AP-3.1-Szenarien koppeln? Vorschlag: konservativ und referenz = Status quo, ambitioniert = Hürden sinken.
3. **Sättigung des Bands:** Soll C_hi künftig aus den Gruppen-Potenzialen abgeleitet werden (Σ N_k · S_k ·
   Dachpotenzial) statt aus dem ganzen Dachpotenzial?
4. **MFH-Anlagengröße (Nebenbefund):** AP 2 zieht MFH-Anlagen aus der MaStR-Verteilung ≤ 30 kW. Reale MFH-Anlagen
   sind meist 30–100 kWp ([Ariadne][ariadne]). Mit Phillip klären, ob MFH eine eigene Größenverteilung bekommen. Das
   ändert, wie viele MFH für das Band nötig sind.
5. **Abgleich Gebäude für Gebäude** (Luftbild-PV-Erkennung, [3D-PV-Locator][pvloc]): als eigenes Arbeitspaket
   aufnehmen, um S und r auf Gebäudeebene in NRW zu messen?

## Quellen

- [kfw19]: KfW Research (2019): KfW-Energiewendebarometer 2019 – Methoden- und Tabellenband. <https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555323>
- [kfw20]: KfW Research (2020): KfW-Energiewendebarometer 2020 – Methoden- und Tabellenband. <https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555341>
- [kfw21]: KfW Research (2021): KfW-Energiewendebarometer 2021 – Methoden- und Tabellenband. <https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555345>
- [kfw22]: KfW Research (2022): KfW-Energiewendebarometer 2022 – Methoden- und Tabellenband. <https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555349>
- [kfw23]: KfW Research (2023): KfW-Energiewendebarometer 2023. <https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555351>
- [kfw24]: KfW Research (2024): KfW-Energiewendebarometer 2024. <https://kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2024.pdf>
- [kfw25]: KfW Research (2025a): KfW-Energiewendebarometer 2025 (Hauptbericht, liegt in `objekttypegenerator/additional-information/`).
- [kfw25t]: KfW Research (2025b): KfW-Energiewendebarometer 2025 – Methoden- und Tabellenband. <https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2025-Methoden-und-Tabellenband.pdf>
- [kfw26]: KfW Research (2026): KfW-Energiewendebarometer 2026 (liegt in `objekttypegenerator/additional-information/`).
- [fokus]: KfW Research (2024): Das Potenzial für Haushaltsphotovoltaik. Fokus Volkswirtschaft Nr. 457. <https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-Fokus-Volkswirtschaft/Fokus-2024/Fokus-Nr.-457-April-2024-Haushalts-PV.pdf>
- [zew]: von Ditfurth, J.; Rausch, S. (2025, rev. 2026): How Cost-Effective Were Subsidies for Solar Energy in Germany? ZEW Discussion Paper 25-018. <https://zew.de/fileadmin/FTP/dp/dp25018.pdf>
- [ariadne]: Fischer, A.; Henger, R. (2025): Gebäude- und Mieterstrom in Deutschland: Potenziale, Wirtschaftlichkeit und regulatorische Handlungsansätze. Kopernikus-Projekt Ariadne. <https://doi.org/10.48485/pik.2025.018>
- [sdge]: SDG&E (2019): EPIC-2 Project 6 Final Report (Bass-Modell je PLZ mit segmentspezifischem Marktpotenzial). <https://sdge.com/sites/default/files/EPIC-2%20Project%206_Final%20Report_0.pdf>
- [iee]: Fraunhofer IEE: AgentHomeID – agentenbasiertes Modell für Investitionen im Wohngebäudebestand. <https://iee.fraunhofer.de/en/application-fields/energy-economics/district-city-region/AgentHomeID.html>
- [pvloc]: Mayer, K. et al. (2022): 3D-PV-Locator: Large-scale detection of rooftop-mounted photovoltaic systems in 3D. Applied Energy 310, 118469. <https://doi.org/10.1016/j.apenergy.2021.118469>

[kfw19]: https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555323
[kfw20]: https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555341
[kfw21]: https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555345
[kfw22]: https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555349
[kfw23]: https://epflicht-hessen.hebis.de/ubffm/download/pdf/8555351
[kfw24]: https://kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2024.pdf
[kfw25]: https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2025.pdf
[kfw25t]: https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2025-Methoden-und-Tabellenband.pdf
[kfw26]: https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-KfW-Energiewendebarometer/KfW-Energiewendebarometer-2026.pdf
[fokus]: https://www.kfw.de/PDF/Download-Center/Konzernthemen/Research/PDF-Dokumente-Fokus-Volkswirtschaft/Fokus-2024/Fokus-Nr.-457-April-2024-Haushalts-PV.pdf
[zew]: https://zew.de/fileadmin/FTP/dp/dp25018.pdf
[ariadne]: https://doi.org/10.48485/pik.2025.018
[sdge]: https://sdge.com/sites/default/files/EPIC-2%20Project%206_Final%20Report_0.pdf
[iee]: https://iee.fraunhofer.de/en/application-fields/energy-economics/district-city-region/AgentHomeID.html
[pvloc]: https://doi.org/10.1016/j.apenergy.2021.118469
