# Methodik-Framework: Die drei Modellkomponenten

Verbindliches Analyseraster für **alle** Technologien. Jedes Technologie-Dokument in `methodik/`
konkretisiert dieses Raster. Die drei Komponenten entsprechen exakt dem Arbeitsplan-Wortlaut:
*theoretisches Potential*, *räumliche Zuordnung*, *zeitliche Entwicklung*.

## 0. Notation & Ergebnisgröße

Grundeinheit ist das **Einfamilienhaus (EFH)**. Für Technologie `k`, NS-Strang `s`, Szenario `z`
und Stützjahr `t ∈ {2030, 2035, 2040, 2045}` (plus Basisjahr `t₀`) liefert AP 3.1:

- `N_k,s` — Zahl der EFH im Strang `s`, die für `k` grundsätzlich in Frage kommen (Potential-Basis)
- `P_k,s,z(t)` — **Durchdringungsgrad** ∈ [0, 1] (Anteil der geeigneten EFH mit `k`)
- `n_k,s,z(t) = P_k,s,z(t) · N_k,s` — Anzahl der Objekte
- `L_k,s,z(t)` — installierte Leistung/Kapazität (kWp, kW, kW_th, kWh) = `n · ø-Größe_k`

Die drei Komponenten liefern nacheinander: **Komponente 1 → `N_k,s` und Sättigung `P_max`**,
**Komponente 2 → welche konkreten EFH (Verortung)**, **Komponente 3 → `P(t)` über die Zeit**.

## 1. Komponente A — Theoretisches Potential

**Frage:** Wie viele EFH im Strang kommen für die Technologie überhaupt in Frage, und wo liegt das
Sättigungsniveau?

**Vorgehen:**
1. **Bestandsbasis:** Zahl der EFH im Netzgebiet/Strang aus **ETHOS.BUILDA** (gebäudescharf,
   `size_class` → EFH, `position` → Strangzuordnung; ergänzt durch Zensus 2022, LoD2, OSM).
2. **Eignungsfilter (technisch):** Anteil geeigneter EFH je Technologie (z.B. PV: nutzbare
   Dachfläche/Ausrichtung; WP: gebäudeseitige Eignung; EV: Stellplatz). Ergebnis: `N_k,s`.
3. **Sättigungsniveau `P_max`:** maximal plausibler Durchdringungsgrad unter den geeigneten EFH,
   abgeleitet aus nationalen Zielpfaden (T45/NEP) und techn./sozioökon. Grenzen.
4. **Heutiger Bestand `P(t₀)`:** aus Registern (MaStR, KBA, BWP) — Startpunkt der Zeitkurve.

Ergebnis: Intervall `[P(t₀), P_max]` als Korridor der Zeitkomponente, plus absolute Basis `N_k,s`.

## 2. Komponente B — Räumliche Zuordnung

**Frage:** *Welche* konkreten EFH im NS-Strang erhalten die Technologie (und in welcher
Reihenfolge beim Hochlauf)?

**Vorgehen — Eignungs-/Wahrscheinlichkeits-Score je EFH.** Empfohlenes Basismodell:
**logistische Adoptions-Regression über geografische + sozioökonomische Faktoren**, einheitlich für
PV/EV/WP und explizit netzbezogen (Bernards 2018, [../literatur.md](../literatur.md) M7). Wichtige
Faktoren dort: Einkommen, Alter, Haushaltszusammensetzung (+ Peer-Effekt bei PV).

- Score `w_i` je Gebäude `i` aus technologiespezifischen Merkmalen (Beispiele):
  - PV: Dachfläche, Ausrichtung/Neigung, Verschattung, Gebäudealter.
  - WP: Baualtersklasse/Sanierungszustand, bisherige Heizart, Fläche.
  - EV: Eigenheim/Stellplatz, Haushaltsgröße/Einkommensproxy.
  - Speicher: **Vorhandensein von PV** (harte Bedingung, s. Kopplung).
- **Peer-/Nachbarschaftseffekt** optional: erhöhte Wahrscheinlichkeit bei Adoptionen in der
  Nachbarschaft (Literatur PV5, PV6) — für räumliche Cluster.
- **Zuordnungsregel:** Beim Hochlauf werden EFH nach absteigendem `w_i` belegt, bis der
  Durchdringungsgrad `P(t)` des jeweiligen Stützjahres erreicht ist (Rank-and-fill). Alternativ
  probabilistische Ziehung proportional zu `w_i` (für Sensitivitäts-Ensembles).

Ergebnis: georeferenzierte Belegung je Stützjahr → direkt an OLT-Netzmodell (AP 3.2) anschlussfähig.

## 3. Komponente C — Zeitliche Entwicklung

**Frage:** Wie entwickelt sich der Durchdringungsgrad `P(t)` vom heutigen Bestand zum
Sättigungsniveau?

**Ansatz — S-Kurven als Backbone.** Die zeitliche Entwicklung wird über **sigmoide
(S-förmige) Diffusionskurven** modelliert. S-Kurven sind der etablierte Standard der
Technologie-Diffusions- und Energiewende-Forschung (logistische Substitution nach Fisher–Pry;
Grübler, Wilson, Nakicenovic; siehe [../literatur.md](../literatur.md) §2a). Begründung: Adoption
verläuft empirisch langsam–schnell–sättigend; S-Kurven sind datenarm kalibrierbar und robust.

Die drei gängigen Varianten gehören **derselben Familie** an und unterscheiden sich in Symmetrie
und Treiber-Interpretation:

- **Logistisch (symmetrische S-Kurve):**
  `P(t) = P_max / (1 + exp(-r · (t − t_m)))` — Wachstumsrate `r`, Wendepunkt `t_m` (bei `P_max/2`).
  Standard-/Default-Fall (Fisher–Pry-Substitution).
- **Gompertz (asymmetrische S-Kurve):** `P(t) = P_max · exp(−b · exp(−c · t))` — früherer
  Wendepunkt, langsamere Sättigung; wenn Zubau früh anzieht und lange ausläuft.
- **Bass (S-Kurve mit externem Term):** kumulierte Adoption über Innovations- (`p`) und
  Imitationskoeffizient (`q`). Bass ist eine **verallgemeinerte logistische Kurve** (`p=0` →
  logistisch); nutzen, wenn Innovations- vs. Peer-/Imitationsanteil getrennt gewünscht sind.

**Kurvenwahl:** logistisch als Default; Gompertz bei erkennbar asymmetrischer Historie; Bass, wenn
Peer-/Imitationsdynamik explizit parametrisiert werden soll. Die Wahl wird je Technologie im
jeweiligen Dokument begründet und per Fit-Güte an der Historie geprüft.

**Substitution & Bestandsumschlag (für Verdrängungstechnologien — WP, EV).** WP und EV ersetzen
einen Altbestand (Gas-/Ölheizung bzw. Verbrenner-Pkw). Der Hochlauf ist dann **kein freies
Wachstum zum `P_max`, sondern ein Substitutionsprozess**, der durch den Umschlag des Altbestands
begrenzt wird (Literatur [../literatur.md](../literatur.md) §2b). Zusätzliche Modellelemente:

- **Bestands-Fluss-Buchhaltung (Erhaltungssatz):** je EFH genau ein Heizsystem, je Haushalt eine
  Pkw-Flotte → Anteile aller konkurrierenden Optionen summieren sich zu 1. Der WP-/EV-Anteil ist das
  Komplement des schrumpfenden Fossilbestands.
- **Ersatz am Lebensende:** Altbestand scheidet gemäß Überlebens-/Survival-Kurve aus
  (Lebensdauer, z.B. Weibull); pro Jahr entsteht ein begrenztes **Ersatzfenster**. Zubau der neuen
  Technologie ≤ Ersatzopportunitäten (+ ggf. vorzeitiger Austausch als Szenariohebel).
- **Wettbewerb an der Ersatzentscheidung:** an jedem Ersatzpunkt konkurriert die neue Technologie mit
  einem *neuen* Fossil-/Alternativsystem (Wahl getrieben von Wirtschaftlichkeit + Politik; FTT-artig).
- **Lock-in:** neu installierte Fossilsysteme binden die Ersatzentscheidung für ihre Lebensdauer →
  Nah-Zeit-Fossileinbauten verzögern den Hochlauf.
- **Politik-Constraints:** GEG-Heizungsgesetz (Fossilkessel-Restriktionen) bzw. EU-Verbrenner-Aus
  2035 als harte/weiche Grenzen des zulässigen Fossil-Neuzubaus.
- **Sales vs. Stock:** relevanter Trägheitseffekt — selbst bei 100 % neuer Technologie im Neuabsatz
  hinkt der **Bestandsanteil** dem **Absatzanteil** um die Umschlagdauer hinterher (SU4).

Praktische Ausgestaltung je Technologie in `waermepumpe.md` bzw. `ev.md`. Die S-Kurve bleibt der
Backbone (für Absatz-/Neuinstallationsanteil); die Bestands-Fluss-Schicht übersetzt sie in den
tatsächlichen Bestandsanteil je Stützjahr.

**Kalibrierung:**
1. Historischen Bestand fitten (MaStR/KBA/BWP-Zeitreihen) → `r`, `t_m` bzw. `p`, `q`.
2. `P_max` und ein Zielstützwert aus nationalen Szenarien (T45/NEP) als Anker → Kurve so
   parametrieren, dass Zielkorridor je Stützjahr getroffen wird.
3. Fit technisch via `scipy.optimize.curve_fit`.

**Downscaling** auf NS-Strang: nationale/regionale Kurve × strangspezifischer Faktor (aus
Komponente A/B), damit lokale Summen zur regionalen Vorgabe konsistent bleiben (vgl. M1).

Ergebnis: `P_k,s,z(t)` je Stützjahr — Input für Komponente B (Verortung).

## 4. Technologie-Kopplungen

Explizit im Modell abzubilden (Reihenfolge der Auflösung):

1. **PV → Batteriespeicher:** Speicher nur bei EFH mit PV; Durchdringung = Kopplungsquote
   (Anteil PV-Anlagen mit Speicher), selbst zeitabhängig.
2. **WP → Wärmespeicher:** dezentraler Pufferspeicher nur bei EFH mit WP; Kopplungsquote analog.

Damit ist die Auswertungsreihenfolge je Stützjahr: **PV, EV, WP → dann Batteriespeicher
(nach PV), Wärmespeicher (nach WP)**.

**Optionale Co-Adoption (Verfeinerung):** Haushalte adoptieren PV/Batterie/WP/EV empirisch
gebündelt („Entry-Point"-Technologien, zeitnahe Bündel; [../literatur.md](../literatur.md) WP-K2).
Über die harten Kopplungen hinaus kann daher eine **Korrelation zwischen den Kern-Technologien** im
Score berücksichtigt werden (z.B. PV-EFH mit erhöhter WP-/EV-Wahrscheinlichkeit). Zunächst optional
bzw. als Sensitivität.

## 5. Szenariologik

Ein **Szenario `z`** ist ein konsistentes Set von Parametern über alle Technologien:
- Sättigungsniveaus `P_max,k`,
- Diffusionsgeschwindigkeiten (`r`/`t_m` bzw. `p`/`q`),
- Kopplungsquoten.

Vorgesehene Ambitionsstufen (Details in `../04_szenarien.md`): *konservativ / Referenz /
ambitioniert*. Alle Parameter werden in reviewbaren SQL-Seeds → SQLite geführt (Reproduzierbarkeit).

## 6. Plausibilisierung (Meilenstein-Anforderung)

- **Summenkonsistenz:** aggregierte Strangwerte ≈ regionale/nationale Zielpfade (T45/NEP).
- **Bestandsplausibilität:** `n_k,s(t) ≤ N_k,s`; Monotonie `P(t)` steigend bis `P_max`.
- **Kopplungskonsistenz:** `n_Speicher ≤ n_PV`, `n_Wärmespeicher ≤ n_WP`.
- **Netzplausibilität (mit OLT):** Größenordnung der Gleichzeitig-Leistungen je Strang sanity-checken.
- Dokumentierte Prüfschritte je Technologie-Dokument (Abschnitt 7).
