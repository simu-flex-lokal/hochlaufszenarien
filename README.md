# Hochlaufszenarien (AP 3.1)

Hochlaufmodell für **SIMU-FLEX LOKAL**, Teilprojekt FH Aachen / NOWUM-Energy.

Das Modell schätzt, wie viel **PV-Leistung (MWp)** eine Gemeinde pro Stützjahr bis 2050
hat. Kern ist ein **probabilistisches
Diffusions-Ensemble** (nach Zielonka et al. 2023), verankert am MaStR-Istwert und
nach oben begrenzt durch das **BUILDA-Dachpotenzial**.

> **Scope:** vorerst nur **PV**. Weitere Technologien (WP, EV, Speicher) kommen später dazu.

## Aufbau

| Ordner | Inhalt |
|---|---|
| `pv_hochlauf/` | Modellpaket: Ensemble (`pipeline/`), BUILDA-Sättigung + DB-Adapter (`io/`), Konfiguration/Modelle (`core/`), Plots (`visualization/`) |
| `db/` | SQLite-Datenmodell (`schema.sql`) + Importer (MaStR, BUILDA, VG250) |
| `docs/` | Methodik (`methodik_pv.md`, Framework, Zielonka-Umstellung), Literatur |
| `examples/` | AP-2-Kopplung (Rand + Live-Run). **Braucht** den ObjectTypeGenerator (AP 2, separates Repo) |

## Schnellstart

```bash
uv sync

# 1) Datenbank anlegen + Quellen importieren
python db/build_db.py
python db/import_mastr.py      # PV-Bestand je Gemeinde (OEDS)
python db/import_builda.py     # Dachpotenzial C_hi

# 2) Hochlauf für eine Gemeinde rechnen (Default: Reichshof)
python pv_hochlauf/run_phase1.py --target 05374040 --builda
```

Ergebnis: Band (p05–p95) der installierten MWp je Stützjahr, persistiert in
`diffusion_ensemble`.

## Methodik in einem Satz

12 Wachstumskurven (S- und Bi-S-Kurven) werden je Gemeinde gefittet, per
Peer-Vergleich zu einem Unsicherheitsband kombiniert und per Walk-Forward-Hindcasting
(WIS) gewichtet. Grundlagen: [`docs/methodik_pv.md`](docs/methodik_pv.md).
