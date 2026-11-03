# Dokumentation: PV-Hochlaufszenarien

Dieses Projekt modelliert den zukünftigen Ausbau von Photovoltaik-Anlagen (PV) auf Gemeindeebene. Es implementiert eine datengetriebene 4-Schritte-Pipeline (in Anlehnung an Zielonka et al., 2023), die verschiedene S-Kurven-Modelle kombiniert, historische Entwicklungen backtestet und Unsicherheiten durch den Vergleich ähnlicher Gemeinden quantifiziert.

---

## 1. Systemvoraussetzungen & Installation

Das Projekt basiert auf Python 3.11+ und nutzt das moderne Build-System `uv` sowie `pyproject.toml`.

### Voraussetzungen
- Python 3.11 oder neuer
- PostgreSQL-Datenbank (für MaStR-Daten) oder ein lokales Pickle-File der Daten.

### Installation
Zur Installation wird im Stammverzeichnis des Projekts (wo die `pyproject.toml` liegt) folgender Befehl ausgeführt:

```bash
# Empfohlen: Installation über uv
uv pip install -e .

# Alternativ über pip
pip install -e .
```
Dadurch werden alle Abhängigkeiten installiert und das Paket lokal verlinkt.

---

## 2. Verwendung

Das Hauptskript führt die gesamte Pipeline aus. Der Start kann auf zwei Arten erfolgen:

**Option 1: Über den installierten Konsolen-Befehl**


Sobald das Paket installiert ist (`uv pip install -e .`), steht systemweit der folgende Befehl zur Verfügung:
```bash
hochlaufszenarien
```

**Option 2: Direkt über Python als Modul**


Alternativ kann das Skript auch explizit über den Python-Modulaufruf gestartet werden:
```bash
python -m pv_hochlauf.pv_hochlauf_main
```

### Datenquellen
Das Skript benötigt historische Ausbaudaten. Standardmäßig versucht `pv_hochlauf_main.py`, eine lokale Datei (`Daten/mastr_data.pkl`) zu laden. 
Wenn direkt aus einer PostgreSQL-Datenbank gelesen werden soll, muss in `pv_hochlauf_main.py` die entsprechende Zeile einkommentiert und die Credentials in `src/pv_hochlauf/io/database.py` in der Funktion `load_mastr_data()` eingetragen werden.

---

## 3. Funktionsweise (Die 4-Schritte-Pipeline)

Das Programm arbeitet in vier iterativen Schritten:

1. **Deterministische Projektionen:** Die historischen Daten jeder Gemeinde werden an 12 verschiedene Wachstumsmodelle (S-Kurven und Bi-S-Kurven) gefittet. Das maximale Ausbaupotenzial ($C_{hi}$) wird dynamisch über Gebäude-Dachflächen (via ETHOS.BUILDA) berechnet (falls eingestellt).
2. **Probabilistische Projektionen:** Um Vorhersage-Unsicherheiten abzubilden, sucht das Programm für jede Gemeinde andere Gemeinden mit einer historisch ähnlichen Wachstumsdynamik. Deren Streuung in der Zukunft bildet das Wahrscheinlichkeitsband (Quantile).
3. **Hindcasting (Backtesting):** Die Modelle werden auf vergangenen Daten getestet (Walk-Forward-Validierung). Über Fehlermetriken (MAPE und WIS) wird bestimmt, welches Modell für welche Gemeinde wie gut funktioniert.
4. **Gewichtetes Ensemble:** Alle Kurven werden entsprechend der Ergebnisse aus Schritt 3 gewichtet und zu einer finalen Szenario-Schar (inkl. konkreter Einzelpfade) zusammengefügt.

---

## 4. Konfiguration & Einstellungsmöglichkeiten

Über die Datei **`src/pv_hochlauf/core/config.py`** können wichtige Konfigurationen vorgenommen werden.

### 4.1 Test-Modus für die Entwicklung
Bei der Weiterentwicklung des Programms dauert ein voller Durchlauf für alle deutschen Gemeinden zu lange.

```python
TEST_MODE = True
```
Der Testmodus reduziert z.B. die Iterationen der Optimierungs-Algorithmen (Differential Evolution), um Berechnungen zu beschleunigen. Die konkreten Parameter für Test- und Produktivläufe können dort auch gesetzt werden.

### 4.2 Ausführung auf bestimmte Zielgemeinden beschränken
Für die Berechnung konkreter Gemeinden wird `TARGET_GEMEINDEN` genutzt. Hierbei sind die **Amtlichen Gemeindeschlüssel (AGS)** als Strings anzugeben.

```python
# Berechnet die kompletten Ergebnisse NUR für diese drei Gemeinden.
# Der erste Schritt wird immer für alle Gemeinden ausgeführt (Referenzpool).
TARGET_GEMEINDEN = ["05358028", "05358024", "09162000"] # Beispiel für [Kreuzau, Jülich, München]

# TARGET_GEMEINDEN = None # Für ganz Deutschland
```

### 4.3 Wohngebäude-Filter
Es lässt sich steuern, ob alle PV-Anlagen simuliert werden, oder z.B. nur Anlagen von Privathaushalten.

```python
FILTER_RESIDENTIAL = True  # False, wenn alle Anlagen genutzt werden sollen
MAX_KWP_RESIDENTIAL = 100.0  # Kappt Anlagen ohne eingetragenen Nutzungsbereich über 100 kWp
RESIDENTIAL_NUTZUNG = ["Haushalt"]
```

### 4.4 Dachflächen-Sättigung (BUILDA)
Standardmäßig wird die ETHOS.BUILDA-Schnittstelle genutzt, um für jede Gemeinde die echte nutzbare Dachfläche abzufragen, um ein realistisches Limit für den PV-Ausbau zu setzen.

```python
USE_BUILDA_SATURATION = True
```
Dies erfordert eine Internetverbindung und den `ethos-builda-client`. Die Daten werden lokal zwischengespeichert und bei einem erneuten Aufruf verwendet. Sollten Daten benötigter Gemeinden Fehlen, werden diese abgerufen und ergänzt.

### 4.5 Caching steuern
Das Programm speichert Zwischenergebnisse in den Ordner `cache_daten`, da die einzelnen Berechnungsschritte sehr rechenintensiv sind.
- Wenn `FORCE_RECOMPUTE = False` gesetzt ist, lädt das Programm bestehende Ergebnisse aus dem Cache.
- `FORCE_RECOMPUTE = True` muss gesetzt werden, wenn z.B. die Konfigurationen für die Berechnung geändert wurden und die Ergebnisse neu berechnet werden sollen.

---

## 5. Ergebnisse (Outputs)

Alle Ergebnisse landen im Ordner **`outputs/`** auf der obersten Ebene des Projekts.

### Ordner `outputs/csv/`
Hier liegen die Rohdaten zur Weiterverarbeitung:
- **`quantile_<Gemeindename>.csv`**: Beinhaltet für jedes Jahr von heute bis 2050 (`PROJ_END`) die errechneten Leistungswerte (in kW) für alle Quantile (z.B. 5%-Quantil bis 95%-Quantil).
- **`pfade_<Gemeindename>.csv`**: Beinhaltet $N$ (z.B. 50) zufällig gezogene, konkrete Szenariopfade (in MWp).

### Ordner `outputs/plots/`
- **`fit_validierung_<Gemeinde>.png`**: Zeigt ein 12er-Grid. Hier ist zu erkennen, wie gut jedes der 12 Modelle an die historischen Daten dieser Gemeinde fittet.
- **`hochlauf_<Gemeinde>.png`**: Die finale Prognose. Auf der linken Seite wird das kontinuierliche Quantilband dargestellt, auf der rechten Seite die konkreten, separierten Szenariopfade.
- **`hindcast_<Gemeinde>.png`**: Eine Heatmap. Sie zeigt grün/rot eingefärbt, welches Modell (Bass, Gompertz etc.) den geringsten Fehler (MAPE/WIS) hatte und entsprechend das höchste Gewicht bekommen hat.
