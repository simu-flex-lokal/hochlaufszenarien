-- Hochlauf-Szenarien AP 3.1 — Seed: nationale Historien EV (KBA) + WP (BWP)
-- Diese Zeitreihen liegen NICHT im OEDS-PostgreSQL vor → gesourcte nationale
-- Stützpunkte (analog referenzpfad). Läuft nach seed_szenarien.sql (Namensordnung
-- 'zeitreihen' > 'szenarien'), da technologie/datenquelle dort angelegt werden.
--
-- IDs aus seed_szenarien (fix): technologie ev=2, wp=3; datenquelle kba=5, bwp=6.
-- Raum 'Deutschland' via Subquery (Auto-ID).
--
-- WICHTIG: ausgewählte, quellenbelegte Stützpunkte (kein lückenloser Jahresgang);
--   für robusten Fit ggf. zu ergänzen (siehe OFFENE_PUNKTE.md).

PRAGMA foreign_keys = ON;

-- Nationale Raumeinheit
INSERT INTO raumeinheit (raum_code, typ, name, quelle_id)
VALUES ('Deutschland', 'land', 'Deutschland', NULL)
ON CONFLICT(raum_code) DO NOTHING;

-- EV: KBA BEV-Pkw-Bestand (Stichtag 1. Januar), national
INSERT INTO historie (technologie_id, raum_id, jahr, wert, groesse, einheit, quelle_id) VALUES
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2017,   34022.0, 'bestand', 'Fahrzeuge', 5),
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2020,  239792.0, 'bestand', 'Fahrzeuge', 5),
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2023, 1000000.0, 'bestand', 'Fahrzeuge', 5),  -- 1-Mio.-Marke
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2024, 1400000.0, 'bestand', 'Fahrzeuge', 5),  -- ~1,4 Mio.
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2025, 1650000.0, 'bestand', 'Fahrzeuge', 5),  -- 1,65 Mio.
 (2, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2026, 2034260.0, 'bestand', 'Fahrzeuge', 5);

-- WP: Bestand Heizungswärmepumpen (Anlagen, national), REKONSTRUIERT.
-- Methode: kumulierter BWP-Jahresabsatz (2010–2025) auf Basisbestand Ende 2009 ≈ 334.000
-- (BWP). Ausmusterung vernachlässigt (WP-Lebensdauer ~20 J., junge Flotte) → leichte
-- Überschätzung; Gegenprobe 2022 ≈ 1,50 Mio. vs. BWP-Angabe ~1,45 Mio. (~4 %). Dient dem
-- Kurvenfit (r/t_m); die 16 monotonen Stützpunkte ersetzen die früheren 2 Bestandspunkte.
-- Quelle: BWP Absatzzahlen (waermepumpe.de/presse/zahlen-daten/absatzzahlen), Abruf 2026-07.
INSERT INTO historie (technologie_id, raum_id, jahr, wert, groesse, einheit, quelle_id) VALUES
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2010,  385000.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2011,  442000.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2012,  501500.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2013,  561500.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2014,  619500.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2015,  676500.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2016,  743000.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2017,  821000.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2018,  905000.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2019,  991300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2020, 1111300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2021, 1265300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2022, 1501300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2023, 1857300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2024, 2050300.0, 'bestand', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2025, 2349300.0, 'bestand', 'Anlagen', 6);

-- WP: BWP Absatz (Heizungs-WP pro Jahr, national) — waermepumpe.de Absatzzahlen
INSERT INTO historie (technologie_id, raum_id, jahr, wert, groesse, einheit, quelle_id) VALUES
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2010,  51000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2011,  57000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2012,  59500.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2013,  60000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2014,  58000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2015,  57000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2016,  66500.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2017,  78000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2018,  84000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2019,  86300.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2020, 120000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2021, 154000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2022, 236000.0, 'absatz', 'Anlagen', 6),
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2023, 356000.0, 'absatz', 'Anlagen', 6),  -- Rekordjahr
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2024, 193000.0, 'absatz', 'Anlagen', 6),  -- -46 %
 (3, (SELECT id FROM raumeinheit WHERE raum_code='Deutschland'), 2025, 299000.0, 'absatz', 'Anlagen', 6);
