# Kernliteratur für die Methodik-Erweiterung (WP · EV · Speicher)

Kuratierte Startliste für die Erweiterung des Hochlaufmodells auf Wärmepumpe, Elektroauto und
Speicher. Nur die **methodisch wichtigsten** Referenzen, je mit anklickbarem DOI und einem Satz,
was sie liefern. Vollständiger Rechercheverlauf: [`literatur.md`](literatur.md).

---

## Gemeinsamer Kern (gilt für alle drei Technologien)

- [Zielonka & Trutnevyte (2025), *iScience*](https://doi.org/10.1016/j.isci.2025.111825) —
  **die direkte Blaupause:** Ensemble aus 72 Diffusionsmodell-Varianten, per Hindcasting validiert
  und gewichtet, für 39 EU-Länder **inkl. WP und BEV**. Unser PV-Modell
  ([Zielonka 2023](https://doi.org/10.1093/pnasnexus/pgad321)) ist die Vorstufe — gleiche Methode,
  neue Technologie.
- [Bernards et al. (2018), *IEEE Trans. Sustain. Energy*](https://doi.org/10.1109/tste.2018.2794579) —
  gemeinsame logistische Adoptions-Regression für **PV, EV und WP** aus sozioökonomischen/räumlichen
  Faktoren. Referenz für die räumliche Verortung (Komponente B).
- **Substitution statt reiner S-Kurve (für WP & EV):** Der Hochlauf verdrängt einen Altbestand
  (Heizung bzw. Verbrenner), dessen Umschlag das Tempo begrenzt → Bestand-Fluss-Buchhaltung.
  [Knobloch et al. (2018), FTT:Heat](https://doi.org/10.1007/s12053-018-9710-0) (Heizungswettbewerb),
  [Held et al. (2021)](https://doi.org/10.1186/s12544-020-00464-0) (Pkw-Lebensdauer/Survival).

---

## Wärmepumpe (WP)

- [Zielonka & Trutnevyte (2025)](https://doi.org/10.1016/j.isci.2025.111825) — **Zeit:** Ensemble-Diffusion mit Hindcast-Validierung (statt Einzelkurve).
- [Arvanitopoulos et al. (2025), *Energy Policy*](https://doi.org/10.1016/j.enpol.2025.114787) — **Raum:** WP-spezifische Determinanten + Spillover (kein Gasnetz, Öl/Festbrennstoff, ländlich, Eigentümer).
- [Knobloch et al. (2018)](https://doi.org/10.1007/s12053-018-9710-0) — **Substitution:** Bottom-up-Wettbewerb fossil ↔ WP, Trägheit, Politik.
- [Zangheri et al. (2017)](https://doi.org/10.1007/s12053-017-9566-8) — **Eignung:** Sanierungslevel je Gebäudetypologie → WP-Machbarkeit (koppelt an BUILDA-Baualter/Sanierung).
- [Ruhnau et al. (2020), *Energy Economics*](https://doi.org/10.1016/j.eneco.2020.104967) — **Treiber:** Wirtschaftlichkeit von WP (DE), für das Szenariotempo.

**Ansatz:** Ensemble-S-Kurve (Zeit, kalibriert an BWP-Absatzhistorie) + logistischer Adoptionsscore
mit WP-Determinanten & Spillover (Raum) + Substitutionsschicht (Altheizung). Details:
[`methodik/waermepumpe.md`](methodik/waermepumpe.md).

---

## Elektroauto (EV)

- [Ensslen et al. (2019)](https://doi.org/10.3390/wevj10040073) — **Architektur:** zweischichtig — top-down Bass (wie viele) + bottom-up logistisch (wer). Das Vorbild für die Umsetzung.
- [Domarchi & Cherchi (2023), *Transport Reviews*](https://doi.org/10.1080/01441647.2023.2195687) — **Review** zu Diffusion **und Substitution**, inklusive Prognosegenauigkeit (RMSE gegen Ist).
- [Jochem et al. (2017), *Transport Reviews*](https://doi.org/10.1080/01441647.2017.1326538) — Methoden-Taxonomie EV-Marktdurchdringung (DE).
- [Held et al. (2021)](https://doi.org/10.1186/s12544-020-00464-0) — **Substitution:** Pkw-Survival/Flottenumschlag — der Grund, warum Zulassungsanteil ≠ Bestandsanteil.
- [Zimm (2020), *Transport Policy*](https://doi.org/10.1016/j.tranpol.2020.12.012) — S-Kurven-Diffusion EV länderübergreifend.
- [Ou et al. (2018)](https://doi.org/10.1016/j.tranpol.2018.04.014) — **Eignung:** privater Stellplatz als Heimlade-Gate (für EFH meist gegeben).

**Ansatz:** S-Kurve für den Neuzulassungsanteil + Flottenumschlag-Schicht → Bestandsanteil; Tempo an
TCO/Förderung/Ladeinfrastruktur gekoppelt. Details: [`methodik/ev.md`](methodik/ev.md).

---

## Speicher (Batterie + Wärmespeicher)

Zwei Modellierungswege für den **Batteriespeicher** — je nach gewünschter Tiefe:

**(a) Einfach — als PV-Folgetechnologie** (Kopplungsquote, unser Default): kein eigenes
Diffusionsmodell, Quote wirtschaftlichkeits-/§14a-getrieben.
- [Arnold et al. (2022), *Energy Economics*](https://doi.org/10.1016/j.eneco.2022.106177) — Netzentgelte/§14a steuern die PV-Speicher-Investition (DE, empirisch).
- [Comello & Reichelstein (2019), *Nature Comm.*](https://doi.org/10.1038/s41467-019-09988-z) — ab wann Heimspeicher wirtschaftlich wird (Zeitpfad der Quote).
- [Hesse et al. (2017)](https://doi.org/10.3390/en10070835) — ökonomisch optimale Speichergröße (Ø-Kapazität).

**(b) Vertieft — Batterie als eigener Diffusionsprozess** (wenn mehr Methodik gewünscht):
- [Fett, Fraunholz & Keles (2021), *Energy Policy*](https://doi.org/10.1016/j.enpol.2021.112543) — **DE:** kalibriertes Prosumer-Diffusionsmodell + agentenbasierte Marktsimulation.
- [Klingler (2017), *Applied Energy*](https://doi.org/10.1016/j.apenergy.2017.08.159) — **DE:** Marktdiffusionsmodell PV+Batterie, erklärt die bisherige Heimspeicher-Entwicklung.

**Wärmespeicher:** als WP-Folgetechnologie mit hoher Kopplungsquote (Puffer ist meist Default), kein
eigenes Diffusionsmodell nötig. Wert belegt durch
[Pena-Bello et al. (2021)](https://doi.org/10.1016/j.enconman.2021.114220) (Wärmespeicher senkt LCOE 13–26 %).

**Ansatz:** Batterie strikt als PV-Folge (Weg a) ist für das Mengengerüst ausreichend und
registerkalibrierbar (MaStR: PV mit Speicher). Weg (b) nur, wenn ein eigenständiger Speicher-Hochlauf
gebraucht wird. Details: [`methodik/batteriespeicher.md`](methodik/batteriespeicher.md),
[`methodik/waermespeicher.md`](methodik/waermespeicher.md).

---

## Co-Adoption (Technologien hängen zusammen)

- [Lagomarsino et al. (2023), *iScience*](https://doi.org/10.1016/j.isci.2023.107815) — Co-Adoptionspfade
  PV/Batterie/WP/EV: „Entry-Point"-Technologien und zeitnahe Bündel-Adoption — nützlich, um die
  Verortung der Folgetechnologien zu verfeinern.
