# Beispiele: AP-2-Kopplung

Diese Skripte koppeln das PV-Hochlaufband (dieses Repo) an den **ObjectTypeGenerator**
(AP 2, Phillip Schlicht — **separates Repo**) und sind deshalb bewusst außerhalb des
Modellkerns.

- `ap2_margin.py` — erzeugt den AP-2-Rand (Durchdringung + Leistung je Gemeinde×Szenario×Jahr).
- `ap2_live_run.py` — verteilt PV auf echte InfDB-Gebäude; kalibriert den PV-Anteil so,
  dass die resultierende Σ MWp das AP-3.1-Ziel trifft.
- `ap2_live_run_reichshof.json` — Ergebnis des Reichshof-Laufs (Referenz).

**Voraussetzungen:** laufende lokale InfDB, der ObjectTypeGenerator und dessen venv.
Die Pfade in den Skripten zeigen auf die ursprünglichen Verzeichnisse und sind vor dem
Lauf anzupassen. Hintergrund: siehe Projektdoku (`infdb_local_setup`, `03_integration`)
im AP-3.1-Hauptrepo.
