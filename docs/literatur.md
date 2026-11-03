# Literatur & Methodenlandschaft

Dokumentation der Literaturrecherche für AP 3.1. Ziel: pro Modellkomponente (Potential / Raum /
Zeit) und Technologie belastbare methodische Referenzen sammeln und daraus die in `methodik/`
verwendeten Ansätze begründen. Primäre Recherchequelle: **OpenAlex**. Ergänzend: graue Literatur
(Referenzszenarien) ohne DOI.

> Status: **erste Sichtung** (automatisiert via OpenAlex, manuell kuratiert). Wird bei der
> Konkretisierung der Methodik iterativ erweitert. Relevanz-Skala: 1 = zentral, 2 = nützlich,
> 3 = Kontext.

## 1. Recherchemethodik (OpenAlex)

- Endpoint: `https://api.openalex.org/works`
- Filter: `from_publication_date:2016-01-01`, `type:article`; Sortierung `relevance_score:desc`;
  `mailto` gesetzt (polite pool).
- Suchbegriffe je Dimension × Technologie (siehe unten). Generische Volltextsuche liefert Rauschen
  (fachfremde Treffer) → **manuelle Kuratierung** zwingend.
- Reproduzierbar geplant als Skript `openalex_search.py`: Queries in YAML, Ausgabe als Tabelle.
  Beispiel-Query (getestet):

```
GET https://api.openalex.org/works
  ?search=rooftop photovoltaic technical potential building GIS estimation
  &filter=from_publication_date:2016-01-01,type:article
  &sort=relevance_score:desc&per-page=4
  &select=doi,title,publication_year,cited_by_count,authorships,primary_location
  &mailto=sejdija@fh-aachen.de
```

Verwendete Suchcluster: `Bass diffusion model`, `logistic/Gompertz S-curve adoption`,
`agent-based adoption residential energy`, `EV adoption diffusion forecasting`,
`EV charging spatial distribution low voltage`, `heat pump adoption/deployment building stock`,
`rooftop PV technical potential GIS`, `residential PV adoption peer effect`,
`residential battery storage adoption self-consumption`, `DER penetration hosting capacity feeder`,
`synthetic building stock GIS bottom-up Germany`.

## 2. Methodische Kernreferenzen (technologieübergreifend)

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Dim. | Rel. |
|---|---|---|---|---|---|
| M1 | Zielonka et al. (2023) | Probabilistic projections of granular energy technology diffusion at subnational level | 10.1093/pnasnexus/pgad321 | Zeit/Raum | 1 |
| M2 | Nemet et al. (2023) | Adoption of historical technologies informs scale-up of emerging measures | 10.1038/s43247-023-01056-1 | Zeit | 2 |
| M3 | Hesselink et al. (2018) | Adoption of energy efficient technologies by households — barriers, policies, ABM | 10.1016/j.rser.2018.09.031 | Zeit/Raum | 1 |
| M4 | Moglia et al. (2017) | Review of agent-based modelling of technology diffusion (residential energy) | 10.1016/j.scs.2017.03.006 | Zeit/Raum | 2 |
| M5 | Sachs et al. (2019) | Agent-based model for energy investment decisions in the residential sector | 10.1016/j.energy.2019.01.161 | Zeit | 2 |
| M6 | Cho et al. (2016) | Technology forecasting using the Fisher–Pry diffusion model | 10.1108/fs-08-2015-0043 | Zeit | 3 |
| M7 | **Bernards et al. (2018)** | **Statistical models for diversified adoption of PV, EV & heat pumps (logistische Regression, netzbezogen)** | 10.1109/tste.2018.2794579 | Raum/Zeit | 1 |

> **M7 ist die zentrale technologieübergreifende Referenz für Komponente B.** Sie schätzt
> Adoptionswahrscheinlichkeiten von **PV, EV und WP gemeinsam** aus geografischen/sozioökonomischen
> Faktoren (Einkommen, Alter, Haushaltszusammensetzung; Peer-Effekt bei PV) und erzeugt daraus eine
> probabilistische, räumliche Durchdringungsprognose für Netze — exakt der Zweck von AP 3.1.

#### §2a — S-Kurven / Diffusionsdynamik (Backbone der Zeitkomponente)

S-förmige (sigmoide) Diffusionskurven sind der etablierte Standard der Technologie-Forecasting- und
Energiewende-Literatur (logistische Substitution, Fisher–Pry). Sie bilden den Backbone der
Komponente C ([methodik/00_framework.md](methodik/00_framework.md) §3).

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Beitrag |
|---|---|---|---|---|
| S1 | Grübler et al. (2016) | Consistent comparisons of the temporal dynamics of energy transitions | 10.1016/j.erss.2016.08.015 | Referenz zu Diffusionsraten/logistischer Dynamik |
| S2 | Nijsse et al. (2023) | The momentum of the solar energy transition | 10.1038/s41467-023-41971-7 | S-Kurven-Momentum Solar, empirische Wachstumsraten |
| S3 | Lowe & Drummond (2021) | Solar, wind and logistic substitution in global energy supply to 2050 | 10.1016/j.rser.2021.111720 | logistische Substitution als Projektionsmethode |
| S4 | Zielonka et al. (2023) | Probabilistic projections of granular energy technology diffusion (subnational) | 10.1093/pnasnexus/pgad321 | probabilistische S-Kurven, subnationales Downscaling |
| S4b | **Zielonka et al. (2025)** | **Probabilities of reaching required diffusion of granular energy techs, 39 EU-Länder (inkl. WP), 2023–2050** | 10.1016/j.isci.2025.111825 | **Ensemble aus 72 Diffusionsmodell-Varianten, per Hindcasting validiert & gewichtet** |
| S5 | Zimm (2020) | EV technology and policy diffusion across countries | 10.1016/j.tranpol.2020.12.012 | S-Kurven-Diffusion speziell EV (für ev.md) |
| S6 | Grübler et al. (2018) | Low energy demand scenario (1.5 °C) | 10.1038/s41560-018-0172-6 | logistisches Up-scaling in Szenariokontext |

**Kurvenwahl (Empfehlung):** logistisch als Default (symmetrisch); Gompertz bei asymmetrischer
Historie; Bass, wenn Innovations-/Imitationsanteil getrennt werden soll. Alle drei sind S-Kurven
derselben Familie (Bass = verallgemeinerte Logistik). Kalibrierung an Registerhistorie (MaStR/KBA/BWP)
+ Zielanker T45/NEP; subnationales Downscaling nach S4.

#### §2b — Substitution & Bestandsumschlag (Konkurrenztechnologie)

Für **WP und EV** ist der Hochlauf primär ein **Substitutionsprozess**: die neue Technologie
verdrängt einen Altbestand (Gas-/Ölheizung bzw. Verbrenner-Pkw), dessen Umschlag den Pfad
**begrenzt**. Reine Nachfrage-S-Kurven greifen zu kurz — das Tempo wird durch Austauschzyklen,
Lebensdauern, Lock-in und Politik (GEG-Heizungsgesetz, EU-Verbrenner-Aus 2035) mitbestimmt.

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Beitrag |
|---|---|---|---|---|
| SU1 | **Knobloch et al. (2018)** | FTT:Heat — Simulation der Dekarbonisierung der Wohnraumheizung (Heizsystem-**Konkurrenz**, Trägheit, Politik) | 10.1007/s12053-018-9710-0 | **Bottom-up-Wettbewerbsmodell fossil↔WP** |
| SU2 | Knobloch et al. (2016) | Behavioural aspect of green tech investments (heterogene Agenten, FTT-Grundlage) | 10.1016/j.eist.2016.03.002 | Technologiewahl bei Ersatz |
| SU3 | **Held et al. (2021)** | Lifespans of passenger cars in Europe — **Flotten-Umschlagmodell, Überlebensraten** | 10.1186/s12544-020-00464-0 | **Pkw-Lebensdauer/Survival als EV-Grenze** |
| SU4 | Woody et al. (2023) | Decarbonization potential of electrifying 50 % of US LDV sales by 2030 | 10.1038/s41467-023-42893-0 | **Sales- vs. Stock-Lücke durch Umschlag** |
| SU5 | Ginster et al. (2025) | Country-specific decarbonization of passenger car fleet (DE/PL/NO), dyn. Stock-Flow-Modell | 10.1111/jiec.70089 | dyn. Bestands-/Flussmodell, Flottenerneuerung (DE) |
| SU6 | Adner & Kapoor (2015) | Innovation ecosystems and the pace of substitution: re-examining S-curves | 10.1002/smj.2363 | Substitutionstempo hängt auch am Altbestand |
| SU7 | Mandel et al. (2023) | Pathways to a net-zero EU building sector (Gebäudebestandsmodell) | 10.1007/s12053-023-10100-0 | Gebäude-Bestandsdynamik/Sanierungsrate |

**Konsequenz für AP 3.1:** WP und EV nicht nur als S-Kurve zum `P_max`, sondern als **Substitution
eines alternden Altbestands** modellieren — mit Bestands-Fluss-Buchhaltung (Erhaltungssatz: je EFH
genau ein Heizsystem; je Haushalt eine Pkw-Flotte), Austausch am Lebensende (Survival-/Weibull),
Lock-in neuer Fossileinbauten und Politik-Constraints. Details in §2b-Anwendung:
[methodik/waermepumpe.md](methodik/waermepumpe.md) und [methodik/ev.md](methodik/ev.md).

**Methodische Einordnung — Zeitliche Entwicklung:** Zwei Familien dominieren. (a) *Aggregierte
Diffusionskurven* (Bass, logistisch, Gompertz, Fisher–Pry) — datenarm, gut kalibrierbar an
Bestandshistorie, liefern Durchdringung(t); M1 zeigt eine probabilistische, subnationale Variante,
die für unser NS-Netz-Downscaling ideal passt. (b) *Agentenbasierte Modelle* (M3–M5) — bilden
Entscheidungsheterogenität, Peer-Effekte und Wirtschaftlichkeit ab, aber datenintensiv.
**Empfehlung AP 3.1:** aggregierte S-Kurven als Basis (robust, reproduzierbar), agentenbasierte
Elemente optional für Sensitivitäten/Peer-Effekte. Passt zur Zuarbeit an JHC (Vorhersagemodelle).

## 3. Technologiespezifische Referenzen

### 3.1 Photovoltaik (PV)

> Vertiefte Recherche (OpenAlex, ~65 Treffer gesichtet, Abstracts der Top-Treffer ausgewertet).
> Ziel: beste Methodik je Komponente identifizieren. Synthese am Ende des Abschnitts.

**Komponente A — Theoretisches Potential**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| PV-A1 | Schlemminger et al. (2024) | Rooftop PV potential by backward ray tracing — DE (Berlin, Köln, Hannover), 2,5 Mio. Dächer, Kosten-Potential-Kurven | 10.1002/pip.3844 | 1 |
| PV-A2 | Mainzer et al. (2017) | Rooftop-PV-Potential auf Stadtebene mit öffentlich verfügbaren Geodaten + Bilderkennung (DE/KIT) | 10.1016/j.solener.2017.06.065 | 1 |
| PV-A3 | Krapf et al. (2022) | Deep Learning für Dachaufbauten in LoD2/3-Modellen — LoD2 überschätzt Potential ~20 % (DE/TUM) | 10.5194/isprs-annals-x-4-w2-2022-161-2022 | 1 |
| PV-A4 | Gagnon et al. (2018) | Rooftop-PV-Potential USA: GIS + LiDAR + statist. Extrapolation (validierter Workflow) | 10.1088/1748-9326/aaa554 | 2 |
| PV-A5 | Joshi et al. (2021) | Globales hochaufgelöstes Rooftop-PV-Potential via Big Data / ML / Geospatial | 10.1038/s41467-021-25720-2 | 2 |

**Komponente C — Zeitliche Diffusion**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| PV-C1 | López Prol (2018) | Regulierung, Wirtschaftlichkeit & Diffusion PV — Vergleich DE/ES (Diffusion = profitabilitätsgetrieben) | 10.1016/j.rser.2018.04.030 | 1 |
| PV-C2 | Dong et al. (2016) | Forecasting residential PV deployment California (Diffusion + Payback-Ökonomie) | 10.1016/j.techfore.2016.11.021 | 1 |
| PV-C3 | da Silva et al. (2022) | Rooftop-PV-Diffusion via Bass-Modell (inkl. „Borrowing" bei fehlender Historie) | 10.13044/j.sdewes.d10.0423 | 2 |
| PV-C4 | Alipour et al. (2021) | End-to-end-Review Residential-PV-Adoption: Theorien, Methoden, Ansätze (199 Studien) | 10.1016/j.renene.2021.01.128 | 1 |

**Komponente B — Räumliche Zuordnung / Peer-Effekte**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| PV-B1 | Zhang et al. (2023) | Neighbourhood-Determinanten Residential-PV NL — Spatial-Durbin (direkt + Spillover) | 10.1016/j.renene.2023.02.118 | 1 |
| PV-B2 | Barnes et al. (2022) | Passive vs. aktive Peer-Effekte, räuml. Diffusion Wohn-PV (Las Vegas) | 10.1016/j.jclepro.2022.132634 | 2 |
| PV-B3 | Kosugi et al. (2019) | Nachbarschaftseinfluss auf PV-Diffusion (Kyoto) | 10.1007/s10018-019-00239-5 | 2 |
| PV-B4 | Scheller et al. (2022) | Welche Peers beeinflussen PV-Adoption in Deutschland | 10.1016/j.erss.2022.102755 | 2 |
| PV-B5 | Zhang et al. (2016) | Data-driven agent-based modeling, Rooftop-Solar-Adoption | 10.1007/s10458-016-9326-8 | 2 |
| PV-B6 | Robinson et al. (2015) | Determinanten raum-zeitlicher Muster der Technologieadoption (ABM) | 10.1016/j.apenergy.2015.04.071 | 2 |
| PV-B7 | Schiera et al. (2019) | GIS + ABM Co-Simulation für Rooftop-PV-Diffusion (Energy Communities) | 10.1109/access.2019.2927446 | 3 |

#### Synthese & empfohlener Ansatz (PV)

- **Potential (A):** In NRW liegt mit dem **Solarkataster (LANUV)** bereits ein dachscharfes
  Ertragspotential vor → *konsumieren statt neu rechnen*; LoD2 (Geobasis NRW) für Geometrie.
  **Wichtige Korrektur (PV-A3):** LoD2 ohne Dachaufbauten überschätzt das Potential ~20 % →
  Eignungs-/Verfügbarkeitsfaktor ansetzen. Größenordnung gegen PV-A1 (DE-Kosten-Potential-Kurven)
  plausibilisieren. Der Workflow von PV-A4 (GIS-Eignung + statist. Extrapolation für Lücken) ist
  die Blaupause, falls Kataster-Lücken bestehen.
- **Zeit (C):** **Bass/logistisch an MaStR-Zubauhistorie fitten** (Historie ist dank MaStR reich,
  „Borrowing" aus PV-C3 nicht nötig). Zentrale Erkenntnis PV-C1/PV-C2: Diffusion ist v.a.
  **wirtschaftlichkeitsgetrieben** → Diffusionsgeschwindigkeit im Szenario an Payback/§14a koppeln,
  nicht als reinen Zeittrend führen. PV-C4 stützt die Methodenwahl (Diffusion vs. ABM vs. statist.).
- **Raum (B):** **Spatial-Durbin-Logik nach PV-B1 (NL, EFH-relevant)** als Vorbild: Adoptions­score
  je EFH aus Einkommen/Immobilienwert, Bebauungsdichte, Gebäude-/Haushaltstyp **plus
  Nachbarschafts-Spillover** (bestätigt durch PV-B2/PV-B3/PV-B4). Umsetzung als gewichteter Score +
  Spillover-Term im rank-and-fill; ABM (PV-B5/PV-B6) nur für Sensitivitäten.
- **Fazit:** PV lässt sich mit vorhandenen deutschen Daten (Solarkataster + LoD2 + MaStR) und
  etablierten Methoden (Bass + wirtschaftlichkeitsgekoppelt, Spatial-Durbin-Score) robust und
  datengetrieben modellieren. Details in [methodik/pv.md](methodik/pv.md).

### 3.2 Elektrofahrzeuge (EV)

> Vertiefte Recherche (OpenAlex, ~68 Treffer gesichtet, Abstracts der Top-Treffer ausgewertet).
> Übergreifend zentral: **M7 (Bernards 2018)** für Komponente B, **§2b** für Substitution/
> Flottenumschlag. Synthese am Ende.

**Methodik / Prognose (übergreifend EV)**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| EV-M1 | **Ensslen et al. (2019)** | Hybrid-Modell FR/DE: top-down **Bass** (wie viele) + bottom-up **binär-logistisch** (wer) + Ladeverhalten | 10.3390/wevj10040073 | 1 |
| EV-M2 | **Jochem et al. (2017)** | Methoden-Taxonomie EV-Marktdurchdringung (bottom-up Choice/ABM vs. top-down Stock/SD/IAM), DE | 10.1080/01441647.2017.1326538 | 1 |
| EV-M3 | Domarchi & Cherchi (2023) | Review EV-Prognosemodelle inkl. Diffusion **& Substitution** + Prognosegenauigkeit | 10.1080/01441647.2023.2195687 | 1 |
| EV-M4 | Daina et al. (2016) | Survey Methoden zur Modellierung der EV-Nutzung | 10.1016/j.rser.2016.10.005 | 3 |

**Komponente A — Potential / Heimlade-Eignung**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| EV-A1 | Ou et al. (2018) | Schätzung der Heim-Parkverfügbarkeit & Effekt auf PEV-Ownership-Kosten (Heimlade-Gate) | 10.1016/j.tranpol.2018.04.014 | 1 |
| EV-A2 | Scorrano et al. (2020) | TCO vollelektr. Pkw: Effekt von Jahresfahrleistung, Heimladen, Stadtfahrt | 10.1016/j.retrec.2019.100799 | 2 |

**Komponente C — Zeitliche Diffusion**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| EV-C1 | Zimm (2020) → S5 | S-Kurven-Diffusion EV länderübergreifend | 10.1016/j.tranpol.2020.12.012 | 1 |
| EV-C2 | Kalthaus & Mao (2021) | Determinanten EV-Diffusion (Subventionen, Politik, Ladeinfrastruktur) | 10.1007/s10640-021-00596-4 | 2 |
| EV-C3 | Broadbent et al. (2022) | EV-Uptake beschleunigen: Politikoptionen Preis & Infrastruktur (Modellierung) | 10.1016/j.tra.2022.05.012 | 2 |
| EV-C4 | Kangur et al. (2017) | Agentenbasiertes Modell der EV-Diffusion | 10.1016/j.jenvp.2017.01.002 | 2 |
| EV-C5 | Knobloch et al. (2020) | Emissionsminderung E-Autos & WP über Zeit (Szenario) | 10.1038/s41893-020-0488-7 | 3 |

**Komponente B — Räumliche Zuordnung / Determinanten**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| EV-B1 | Bernards et al. (2018) → M7 | Logistische Adoptions-Regression PV/EV/WP, netzbezogen | 10.1109/tste.2018.2794579 | 1 |
| EV-B2 | Sovacool et al. (2018) | Demografie der E-Mobilität (Geschlecht, Bildung, Beruf, Alter, Haushaltsgröße), Nordics | 10.1016/j.gloenvcha.2018.06.008 | 2 |
| EV-B3 | Manca et al. (2020) | Einfluss von Peer-Einstellungen auf EV-Wahlverhalten (Peer-Effekt) | 10.1016/j.tra.2020.08.016 | 2 |
| EV-B4 | Zhuge & Shao (2018) | Faktoren der EV-Aufnahme Beijing: statistisch & räumlich | 10.1016/j.jclepro.2018.12.099 | 2 |
| EV-B5 | de Rubens (2019) | ML-Segmentierung des EV-Mainstream-Markts (Preis als Haupttreiber) | 10.1016/j.energy.2019.01.114 | 3 |

**Netzbezug (Kontext Komponente B / Übergabe AP 3.2)**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| EV-N1 | Powell et al. (2022) | Ladeinfrastruktur-Zugang/-Betrieb zur Reduktion der Netzwirkung tiefer EV-Adoption | 10.1038/s41560-022-01105-7 | 2 |
| EV-N2 | Deb et al. (2018) | Wirkung der EV-Ladelast auf das Verteilnetz | 10.3390/en11010178 | 2 |

#### Synthese & empfohlener Ansatz (EV)

- **Architektur (EV-M1/Ensslen 2019):** **zweischichtig** — top-down S-Kurve für den aggregierten
  BEV-Anteil + bottom-up logistischer „wer-adoptiert"-Score. Methoden-Taxonomie EV-M2/Jochem 2017;
  Diffusion+Substitution + Genauigkeitscaveats EV-M3/Domarchi 2023.
- **Potential (A):** Basis = EFH-Haushalte mit Pkw (BUILDA-EFH × Zensus/KBA). **Heimlade-Gate =
  privater Stellplatz** (EV-A1) — für EFH weitgehend gegeben → EFH privilegiert. `P_max` hoch
  (T45, EU-Verbrenner-Aus 2035).
- **Zeit (C):** S-Kurve für Neuzulassungsanteil (EV-C1) **+ Flottenumschlag-Schicht (§2b)** →
  Bestandsanteil. Tempo an TCO/Preis, Förderung, Ladeinfrastruktur koppeln (EV-C2, EV-C3, EV-B5).
- **Raum (B):** M7-Score + EV-Sozidemografie (EV-B2: Haushaltsgröße, Bildung, Beruf, Alter) +
  **Peer-Effekt** (EV-B3) + Heimlade-Gate (EV-A1); konkrete Umsetzung = binär-logistisch nach EV-M1.
- **Fazit:** EV wie PV/WP mit Zwei-Schichten-Modell robust modellierbar; Besonderheit gegenüber PV
  ist die **Flottenträgheit** (Sales≠Stock, §2b). Details in [methodik/ev.md](methodik/ev.md).

### 3.3 Wärmepumpe (WP)

> Vertiefte Recherche (OpenAlex, ~68 Treffer gesichtet, Abstracts der Top-Treffer ausgewertet).
> Übergreifend zentral: **M7 (Bernards 2018)** für Komponente B, **S4b (Zielonka 2025)** für
> Komponente C (beide oben). Synthese am Ende.

**Komponente A — Eignung / Potential (Baualter, Sanierung, Heizart)**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| WP-A1 | Zangheri et al. (2017) | Kostenoptimale/NZEB-Sanierungslevel je Gebäudetypologie (EU) — koppelt Sanierungszustand an WP-Eignung | 10.1007/s12053-017-9566-8 | 1 |
| WP-A2 | Abbasi et al. (2021) | Heat transition EU über WP-Technologie; hybride WP für schwer sanierbaren Bestand | 10.1016/j.seta.2021.101630 | 1 |
| WP-A3 | Billerbeck et al. (2023) | WP vs. H₂ für Raum-/Warmwasser (EU-Szenario): WP-Pfade ≥11 % günstiger → hoher `P_max` | 10.1016/j.enconman.2023.117850 | 1 |
| WP-A4 | Le et al. (2019) | Techno-ökon. Bewertung Luft-Wasser-WP-Retrofit in Wohngebäuden (validierte Simulation) | 10.1016/j.apenergy.2019.05.041 | 2 |
| WP-A5 | Berrill et al. (2022) | Dekarbonisierungspfade Wohnsektor (Gebäudebestand) | 10.1038/s41558-022-01429-y | 2 |

**Komponente C — Zeitliche Diffusion**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| WP-C1 | Zielonka et al. (2025) → S4b | Ensemble-Diffusion WP, 39 EU-Länder, hindcast-validiert | 10.1016/j.isci.2025.111825 | 1 |
| WP-C2 | Meles et al. (2022) | Agentenbasiertes Modell der WP-Adoption (Irland) | 10.1016/j.rser.2022.112853 | 2 |
| WP-C3 | Ruhnau et al. (2020) | Ökonomie von WP & variablen Erneuerbaren (Diffusionstreiber Wirtschaftlichkeit, DE) | 10.1016/j.eneco.2020.104967 | 2 |
| WP-C4 | Camarasa et al. (2022) | Globaler Vergleich Gebäude-Dekarbonisierungsszenarien 2050 | 10.1038/s41467-022-29890-5 | 2 |
| WP-C5 | Lamb et al. (2024) | Steigerung der WP-Adoption: Home-Readiness (UK) | 10.1007/s43979-024-00084-w | 3 |

**Komponente B — Räumliche Zuordnung / Determinanten**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| WP-B1 | Bernards et al. (2018) → M7 | Logistische Adoptions-Regression PV/EV/WP, netzbezogen | 10.1109/tste.2018.2794579 | 1 |
| WP-B2 | Arvanitopoulos et al. (2025) | Lokale Bedingungen & räuml. Spillover der WP-Diffusion (GB): off-gas-grid, Öl/Festbrennstoff, ländlich, Eigentümer | 10.1016/j.enpol.2025.114787 | 1 |
| WP-B3 | McGarry et al. (2023) | Hochauflösende geospatiale Socio-Technical-Methodik: E-Wärme/-Verkehr → Verteilnetz (Trafo-Headroom) | 10.1016/j.segan.2023.101118 | 1 |
| WP-B4 | McCoy et al. (2018) | Räuml.-zeitl. Determinanten der Gas-Zentralheizung-Adoption (analoge Heizungs-Diffusion) | 10.1016/j.reseneeco.2017.12.004 | 2 |

**Kopplung / Co-Adoption**

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Rel. |
|---|---|---|---|---|
| WP-K1 | Pena-Bello et al. (2021) | PV-gekoppelte WP + Strom-/Wärmespeicher (EFH): Wärmespeicher senkt LCOE 13–26 % | 10.1016/j.enconman.2021.114220 | 1 |
| WP-K2 | Lagomarsino et al. (2023) | Co-Adoptionspfade (PV/Batterie/WP/EV): „Entry-Point"-Technologien, zeitnahe Bündel-Adoption | 10.1016/j.isci.2023.107815 | 2 |

#### Synthese & empfohlener Ansatz (WP)

- **Eignung/Potential (A):** Basis = alle EFH aus **ETHOS.BUILDA**. Eignungsfilter aus
  `construction_year`, `refurbishment_state`, `tabula_type` (BUILDA) → Retrofit-Level bestimmt
  Machbarkeit (WP-A1); für unsanierten Altbau hybride/bivalente WP (WP-A2). Zusätzlich Heizart &
  **Gasnetz-Anschluss** als Treiber (WP-B2, WP-B4; Heizart aus Zensus, da BUILDA sie nicht führt).
  `P_max` hoch, da WP der kostenoptimale Wärmepfad ist (WP-A3; DE: WP-A3/Altermatt) — konsistent zu T45.
- **Zeit (C):** **Ensemble-Diffusion mit Hindcast-Validierung nach WP-C1 (Zielonka 2025)** statt
  Einzelkurve; kalibriert an **BWP-Absatzhistorie**; Geschwindigkeit wirtschaftlichkeits-/
  förder-getrieben (WP-C3, BEG). ABM (WP-C2) für Verhaltens-Sensitivitäten optional.
- **Raum (B):** Score nach **M7/WP-B1** (Einkommen, Alter, Haushaltstyp) **+ WP-spezifische
  Determinanten WP-B2** (off-gas-grid, Öl/Festbrennstoff-Vorheizung, Eigentümer/EFH, ländlich) **+
  räumlicher Spillover** (Installateur-/Lieferketten-Effekt). WP-B3 als Brücke zur Netzebene (AP 3.2).
- **Kopplung:** WP→Wärmespeicher über Kopplungsquote (Wert des Wärmespeichers belegt WP-K1). Optional
  **Co-Adoptions-Korrelation** (WP-K2) zwischen PV/EV/WP/Speicher als Verfeinerung der Verortung.
- **Fazit:** WP profitiert am stärksten von BUILDA (Baualter/Sanierung gebäudescharf). Methodik:
  Ensemble-S-Kurven (Zeit) + logistischer Adoptionsscore mit WP-Determinanten & Spillover (Raum).
  Details in [methodik/waermepumpe.md](methodik/waermepumpe.md).

### 3.4 Batteriespeicher (an PV gekoppelt)

> Folgetechnologie → Recherchefokus: **Kopplungsquote** (Anteil PV-Anlagen mit Speicher), deren
> **wirtschaftlicher/zeitlicher** Verlauf und **Ø-Größe**. Kein eigenes Potential-/Substitutionsmodell.

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Dim. | Rel. |
|---|---|---|---|---|---|
| BS1 | Zakeri et al. (2021) | Policy options for economic profitability of residential PV + battery storage | 10.1016/j.apenergy.2021.116697 | Zeit/Ökon | 1 |
| BS2 | Comello & Reichelstein (2019) | The emergence of cost-effective battery storage | 10.1038/s41467-019-09988-z | Zeit/Ökon | 1 |
| BS3 | **Arnold et al. (2022)** | Netzentgelte steuern Residential-PV(-Speicher)-Investition unter Net-Purchasing (DE, empirisch) | 10.1016/j.eneco.2022.106177 | Zeit/Ökon | 1 |
| BS4 | Hesse et al. (2017) | Ökonomisch optimale Dimensionierung residentieller PV-BESS (Ø-Größe) | 10.3390/en10070835 | Größe | 2 |
| BS5 | Ciocia et al. (2021) | Self-Consumption/-Sufficiency PV: Effekt von Netzlimit & Speicher (Sizing) | 10.3390/en14061591 | Größe | 2 |
| BS6 | Jannesar et al. (2018) | Optimale Platzierung/Dimensionierung von Batteriespeichern in NS-Netzen mit hoher PV | 10.1016/j.apenergy.2018.06.036 | Raum | 3 |

**Synthese (Batteriespeicher):** Modellierung strikt als **PV-Folgetechnologie** — Kopplungsquote
statt Potentialrechnung. `N_BS,s(t) = n_PV,s(t)`. Zeitpfad der Quote **wirtschaftlichkeitsgetrieben**
(BS1, BS2) und **netzentgelt-/§14a-sensitiv** (BS3, DE — hoher Projektbezug: zeitvariable Entgelte
erhöhen den Speicheranreiz). Ø-Kapazität aus MaStR-Verteilung bzw. Sizing-Logik (BS4, BS5; Speicher
skaliert mit PV-Größe & Eigenverbrauchsziel). Ist-Kopplungsquote direkt aus **MaStR** (PV mit
registriertem Speicher). Details in [methodik/batteriespeicher.md](methodik/batteriespeicher.md).

### 3.5 Dezentraler Wärmespeicher (an WP gekoppelt, nachrangig)

> Folgetechnologie → Recherchefokus: Kopplungsquote zur WP und **Flexibilitätsrolle**. Die Literatur
> behandelt Pufferspeicher fast ausschließlich als **Flexibilitäts-/Demand-Response-Element**, kaum
> als eigenen Adoptionsprozess (Puffer ist meist Default-Bestandteil einer WP-Installation).

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Dim. | Rel. |
|---|---|---|---|---|---|
| WS1 | Pena-Bello et al. (2021) → WP-K1 | PV-gekoppelte WP + Wärmespeicher (EFH): Wärmespeicher senkt LCOE 13–26 % | 10.1016/j.enconman.2021.114220 | Ökon/Flex | 1 |
| WS2 | Patteeuw et al. (2015) | Integrierte Modellierung aktiver DR mit E-Heizsystemen + Wärmespeicher | 10.1016/j.apenergy.2015.04.014 | Flex | 2 |
| WS3 | Dengiz et al. (2019) | Demand Response mit modulierenden Wärmepumpen (DE) | 10.1016/j.apenergy.2018.12.008 | Flex | 2 |
| WS4 | Masy et al. (2015) | Netzflexible Gebäude über WP + thermische Masse als Speicher | 10.1080/23744731.2015.1035590 | Flex | 3 |

**Synthese (Wärmespeicher):** als **WP-Folgetechnologie** mit **einfacher, hoher Kopplungsquote**
modellieren (`N_WS,s(t) = n_WP,s(t)`), da Puffer meist Default. Kein eigenes Diffusionsmodell nötig.
Der Mehrwert (Flexibilität für §14a/AP 2) ist über WS1–WS4 belegt, liegt aber im Betrieb (AP 2),
nicht im Mengengerüst. Details in [methodik/waermespeicher.md](methodik/waermespeicher.md).

### 3.6 Netz-/Durchdringungskontext (für räumliche Zuordnung & Plausibilisierung)

| Ref | Autor:in (Jahr) | Titel (Kurz) | DOI | Dim. | Rel. |
|---|---|---|---|---|---|
| N1 | Fatima et al. (2020) | Review on PV hosting capacity in distribution networks | 10.3390/en13184756 | Raum | 2 |
| N2 | Ustun et al. (2019) | Impact of smart inverters on feeder hosting capacity | 10.1109/access.2019.2952569 | Raum | 3 |
| N3 | Ang et al. (2020) | Review of use cases in urban building energy modeling | 10.1016/j.apenergy.2020.115738 | Raum | 2 |
| N4 | Haberl et al. (2021) | High-resolution maps of building material stocks (AT/DE) | 10.1021/acs.est.0c05642 | Raum | 3 |
| N5 | [Gupta et al. (2021)](https://doi.org/10.1016/j.apenergy.2021.116504) | Spatial analysis of distribution grid capacity for PV, e-mobility & e-heating (CH, ~170k Haushalte) | 10.1016/j.apenergy.2021.116504 | Raum | 1 |

> **N5 (nächster Konkurrent, am Original verifiziert):** PV+WP+EV auf NS-Netz, GIS, ~170 000 Haushalte,
> Schweiz. **Exogene** Penetrations-Szenarien (2035/2050), keine Diffusionsmodellierung; Batterie nur als
> Netzverstärkungs-Aufschub. Abgrenzung AP 3.1: **endogene, registerkalibrierte Diffusion** statt exogener
> Szenarien; DE-EFH; gekoppelte Speicher-Adoption. Siehe [FORSCHUNGSLUECKE.md](FORSCHUNGSLUECKE.md) §3.

## 4. Referenzszenarien & Zielpfade (graue Literatur, ohne DOI)

Diese liefern die **nationalen Sättigungs- und Zeitanker**, an die die Diffusionskurven kalibriert
werden. Vor Nutzung jeweils aktuellste Fassung prüfen und mit Datum zitieren.

| Quelle | Herausgeber | Nutzung in AP 3.1 |
|---|---|---|
| Langfristszenarien (T45-Szenarien) | BMWK / Fraunhofer ISI, Consentec u.a. | Zielkorridore PV, WP, EV-Bestand bis 2045 |
| Netzentwicklungsplan Strom (NEP) | Übertragungsnetzbetreiber / BNetzA | Rahmendaten Elektrifizierung, EV/WP-Hochlauf |
| Ariadne-Report (Szenarien) | Kopernikus-Projekt Ariadne / PIK | Alternative Pfad-Bandbreiten, Sektorkopplung |
| Agora Energiewende — Klimaneutrales Deutschland | Agora Energiewende | Vergleichs-/Ambitionspfade |
| dena-Leitstudie / Gebäudereport | Deutsche Energie-Agentur | Gebäude-/Heizungsbestand, WP-Pfad |
| BWP-Absatzstatistik | Bundesverband Wärmepumpe | Historischer WP-Absatz (Kurvenkalibrierung) |
| KBA Zulassungsstatistik | Kraftfahrt-Bundesamt | EV-Bestand/-Zulassungen (regional) |
| Marktstammdatenregister (MaStR) | Bundesnetzagentur | PV-/Heimspeicher-Bestand (georeferenziert) |
| ETHOS.BUILDA (10.5281/zenodo.12069755) | FZ Jülich IEK-3 | gebäudescharfe EFH-Basis: Baujahr, Größenklasse, Sanierungszustand, TABULA-Typ (NRW=DEA) |
| Zensus 2022 | Statistische Ämter des Bundes und der Länder | EFH-Bestand, Heizungsart, Gebäudealter (aggregiert) |
| Solarkataster NRW | LANUV NRW / Geobasis NRW | Dachflächen-/Ertragspotential PV |

## 5. Offene Punkte / Recherchelücken

- WP-**Diffusions**studien mit deutschem Fokus dünn → BWP-Absatzdaten + T45 als primärer Anker,
  Literatur v.a. für Methode (WP1, WP4).
- Deutschsprachige, NS-netzscharfe **Downscaling**-Methoden gezielt nachrecherchieren (M1 als
  methodischer Startpunkt für subnationale Diffusion).
- Peer-/Nachbarschaftseffekte (PV5, PV6) für die räumliche Zuordnung vertiefen.
- `openalex_search.py` implementieren, um diese Tabellen reproduzierbar zu aktualisieren.
