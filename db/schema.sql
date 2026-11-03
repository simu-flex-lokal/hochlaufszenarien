-- Hochlauf-Szenarien AP 3.1 — SQLite-Schema (autoritativ)
-- Dokumentierter Entwurf/Rationale: ap3_1_hochlaufszenarien/05_datenmodell.md
-- SQLite >= 3.37 (STRICT-Tabellen). FKs zur Laufzeit aktivieren.

PRAGMA foreign_keys = ON;

-- ============================================================
-- Schicht 1: Metadaten / Provenienz
-- ============================================================
CREATE TABLE datenquelle (
  id           INTEGER PRIMARY KEY,
  code         TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  herausgeber  TEXT,
  url          TEXT,
  doi          TEXT,
  lizenz       TEXT,
  stand        TEXT,
  abrufdatum   TEXT,
  version      TEXT,
  beschreibung TEXT
) STRICT;

CREATE TABLE import_log (
  id             INTEGER PRIMARY KEY,
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id),
  ziel_tabelle   TEXT NOT NULL,
  zeilen         INTEGER,
  skript_version TEXT,
  importiert_am  TEXT NOT NULL
) STRICT;

-- ============================================================
-- Schicht 2: Referenz / Parameter (aus Seeds)
-- ============================================================
CREATE TABLE technologie (
  id               INTEGER PRIMARY KEY,
  code             TEXT NOT NULL UNIQUE,
  name             TEXT NOT NULL,
  typ              TEXT NOT NULL CHECK (typ IN ('kern','folge')),
  basis_code       TEXT REFERENCES technologie(code),
  ist_substitution INTEGER NOT NULL DEFAULT 0,
  beschreibung     TEXT
) STRICT;

CREATE TABLE szenario (
  id           INTEGER PRIMARY KEY,
  code         TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  referenzpfad TEXT,
  quelle_id    INTEGER REFERENCES datenquelle(id),
  beschreibung TEXT
) STRICT;

CREATE TABLE parameter_def (
  code         TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  einheit      TEXT,
  gilt_fuer    TEXT,
  beschreibung TEXT
) STRICT;

CREATE TABLE szenario_parameter (
  id             INTEGER PRIMARY KEY,
  szenario_id    INTEGER NOT NULL REFERENCES szenario(id),
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  parameter      TEXT NOT NULL REFERENCES parameter_def(code),
  wert           REAL NOT NULL,
  einheit        TEXT,
  quelle_id      INTEGER REFERENCES datenquelle(id),
  kommentar      TEXT,
  UNIQUE (szenario_id, technologie_id, parameter)
) STRICT;

CREATE TABLE kopplung (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  basis_id       INTEGER NOT NULL REFERENCES technologie(id),
  art            TEXT NOT NULL CHECK (art IN ('hart','co_adoption')),
  beschreibung   TEXT
) STRICT;

-- ============================================================
-- Schicht 3: Rohdaten (jeweils mit quelle_id)
-- ============================================================
CREATE TABLE raumeinheit (
  id               INTEGER PRIMARY KEY,
  raum_code        TEXT NOT NULL UNIQUE,
  typ              TEXT NOT NULL,
  name             TEXT,
  uebergeordnet_id INTEGER REFERENCES raumeinheit(id),
  geom_wkt         TEXT,
  quelle_id        INTEGER REFERENCES datenquelle(id)
) STRICT;

CREATE TABLE gebaeude (
  id                INTEGER PRIMARY KEY,
  externe_id        TEXT,
  raum_id           INTEGER REFERENCES raumeinheit(id),
  geom_wkt          TEXT,
  gebaeudetyp       TEXT,
  baujahr           INTEGER,
  sanierung         TEXT,
  tabula_typ        TEXT,
  heizart           TEXT,
  gasnetz_anschluss INTEGER,
  baujahr_source    TEXT, baujahr_lineage   TEXT,
  sanierung_source  TEXT, sanierung_lineage TEXT,
  tabula_source     TEXT, tabula_lineage    TEXT,
  quelle_id         INTEGER REFERENCES datenquelle(id)
) STRICT;

CREATE TABLE potenzial (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  gebaeude_id    INTEGER REFERENCES gebaeude(id),
  raum_id        INTEGER REFERENCES raumeinheit(id),
  eignung        INTEGER,
  potenzial_wert REAL,
  einheit        TEXT,
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id),
  CHECK (gebaeude_id IS NOT NULL OR raum_id IS NOT NULL)
) STRICT;

-- Regionaler Eignungsanteil je Technologie/Raum (0..1), quellenbelegt.
-- Ersetzt in potential.py den pauschalen Eignungsfaktor, wo eine datengestützte
-- gebäudescharfe Quelle vorliegt (z.B. FfE Wärmepumpen-Ampel für WP je Gemeinde).
CREATE TABLE eignung_regional (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  raum_id        INTEGER NOT NULL REFERENCES raumeinheit(id),
  anteil         REAL NOT NULL CHECK (anteil >= 0 AND anteil <= 1),
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id),
  kommentar      TEXT,
  UNIQUE (technologie_id, raum_id, quelle_id)
) STRICT;

-- Technologieweiter Default-Eignungsanteil (0..1), falls keine regionale Quelle
-- vorliegt. In potential.py der Fallback hinter eignung_regional. quelle_id NULL =
-- bewusst unbelegter Erstwert (keine fest verdrahteten Zahlen im Code, aber ehrlich
-- als unbelegt markiert, bis eine Datenquelle die Herleitung liefert).
CREATE TABLE eignung_faktor (
  technologie_id INTEGER PRIMARY KEY REFERENCES technologie(id),
  anteil         REAL NOT NULL CHECK (anteil >= 0 AND anteil <= 1),
  quelle_id      INTEGER REFERENCES datenquelle(id),
  kommentar      TEXT
) STRICT;

CREATE TABLE bestand_ist (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  raum_id        INTEGER REFERENCES raumeinheit(id),
  gebaeude_id    INTEGER REFERENCES gebaeude(id),
  jahr           INTEGER NOT NULL,
  anzahl         INTEGER,
  leistung_kw    REAL,
  kapazitaet_kwh REAL,
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id)
) STRICT;

CREATE TABLE historie (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  raum_id        INTEGER REFERENCES raumeinheit(id),
  jahr           INTEGER NOT NULL,
  wert           REAL NOT NULL,
  groesse        TEXT NOT NULL CHECK (groesse IN ('bestand','zubau','absatz')),
  einheit        TEXT NOT NULL,   -- 'Anlagen' | 'kW' | 'kWh' (Metrik der Zeitreihe)
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id)
) STRICT;

CREATE TABLE referenzpfad (
  id             INTEGER PRIMARY KEY,
  pfad           TEXT NOT NULL,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  jahr           INTEGER NOT NULL,
  wert           REAL NOT NULL,
  einheit        TEXT,
  quelle_id      INTEGER NOT NULL REFERENCES datenquelle(id),
  kommentar      TEXT
) STRICT;

-- Abgeleitete Analyse: gefittete Diffusionskurven (Komponente C)
CREATE TABLE diffusion_fit (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  raum_id        INTEGER REFERENCES raumeinheit(id),
  modell         TEXT NOT NULL CHECK (modell IN ('logistisch','gompertz','bass')),
  p_max          REAL,                         -- Sättigung (absolut, Einheit der Reihe)
  r              REAL,                          -- Wachstumsrate
  t_m            REAL,                          -- Wendepunktjahr
  param_json     TEXT,                          -- Zusatzparameter (z.B. Bass p/q)
  einheit        TEXT,                          -- Metrik der Reihe (Anlagen/kW/…)
  rmse           REAL,
  n_punkte       INTEGER,
  jahr_von       INTEGER,
  jahr_bis       INTEGER,
  p_max_fixiert  INTEGER NOT NULL DEFAULT 0,    -- 1 = p_max vorgegeben (nicht gefittet)
  quelle_id      INTEGER REFERENCES datenquelle(id),
  fit_am         TEXT NOT NULL
) STRICT;

-- Zeitkomponente (Komponente C), NEU: probabilistisches Zielonka-Ensemble-Band.
-- Löst die Einzel-Logistik (diffusion_fit) als produktive Zeitkomponente ab: je Technologie/
-- Raum/Stützjahr ein Quantil-Band (12-Modell-Ensemble, hindcast-gewichtet, BUILDA-Sättigung).
-- Erzeugt von hochlauf_model/pv_hochlauf (run_phase1.py → io/db_persist.py).
CREATE TABLE diffusion_ensemble (
  id             INTEGER PRIMARY KEY,
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  raum_id        INTEGER NOT NULL REFERENCES raumeinheit(id),
  stuetzjahr     INTEGER NOT NULL,
  quantil        REAL NOT NULL,                 -- 0.05 / 0.25 / 0.50 / 0.75 / 0.95
  wert           REAL NOT NULL,                 -- kumulierter Bestand in 'einheit'
  einheit        TEXT NOT NULL,                 -- 'MWp' | 'Anlagen'
  modell         TEXT NOT NULL DEFAULT 'zielonka-ensemble',
  meta_json      TEXT,                          -- n_similar, Top-Modellgewichte, C_hi
  quelle_id      INTEGER REFERENCES datenquelle(id),
  erstellt_am    TEXT NOT NULL,
  UNIQUE (technologie_id, raum_id, stuetzjahr, quantil, einheit)
) STRICT;

-- ============================================================
-- Schicht 4: Ergebnis
-- ============================================================
CREATE TABLE lauf (
  id           INTEGER PRIMARY KEY,
  code         TEXT UNIQUE,
  git_commit   TEXT,
  erstellt_am  TEXT NOT NULL,
  beschreibung TEXT
) STRICT;

CREATE TABLE mengengeruest (
  id             INTEGER PRIMARY KEY,
  lauf_id        INTEGER NOT NULL REFERENCES lauf(id),
  szenario_id    INTEGER NOT NULL REFERENCES szenario(id),
  technologie_id INTEGER NOT NULL REFERENCES technologie(id),
  stuetzjahr     INTEGER NOT NULL,
  raum_id        INTEGER REFERENCES raumeinheit(id),
  gebaeude_id    INTEGER REFERENCES gebaeude(id),
  durchdringung  REAL,
  anzahl         INTEGER,
  leistung_kw    REAL,
  kapazitaet_kwh REAL
) STRICT;

CREATE TABLE plausibilisierung (
  id         INTEGER PRIMARY KEY,
  lauf_id    INTEGER NOT NULL REFERENCES lauf(id),
  check_name TEXT NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('ok','warnung','fehler')),
  detail     TEXT
) STRICT;

CREATE INDEX ix_mengengeruest_query ON mengengeruest (szenario_id, stuetzjahr, raum_id);
CREATE INDEX ix_gebaeude_raum       ON gebaeude (raum_id);
CREATE INDEX ix_potenzial_tech      ON potenzial (technologie_id);
