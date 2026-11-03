-- Hochlauf-Szenarien AP 3.1 — Seed: Referenz/Parameter + T45-Zielpfade
-- Reviewbare Quelle der Parameterwerte (git). Anwenden nach schema.sql.
-- Doku: ap3_1_hochlaufszenarien/04_szenarien.md, 05_datenmodell.md
--
-- HINWEIS ZUR HERKUNFT:
--   referenzpfad      = reale, quellenbelegte T45-/EEG-Absolutwerte (national).
--   szenario_parameter = daraus ABGELEITETE Modellparameter (Erstwerte, tlw. vorläufig).
--   r (Wachstumsrate) bleibt offen -> Kurvenfit an MaStR/KBA/BWP (siehe OFFENE_PUNKTE.md).

PRAGMA foreign_keys = ON;

-- ============================================================
-- Datenquellen-Registry (Provenienz)
-- ============================================================
INSERT INTO datenquelle (id,code,name,herausgeber,url,doi,lizenz,stand,abrufdatum,version,beschreibung) VALUES
 (1,'t45','Langfristszenarien 3 (T45)','BMWK / Fraunhofer ISI, Consentec, ifeu, TU Berlin','https://langfristszenarien.de',NULL,NULL,'2023','2026-07-23','LFS3 / T45','T45-Szenarienfamilie, Klimaneutralität 2045'),
 (2,'eeg','EEG 2023 PV-Ausbaupfad','Bundesregierung','https://www.gesetze-im-internet.de/eeg_2014/',NULL,NULL,'2023',NULL,NULL,'Gesetzlicher PV-Ausbaupfad (u.a. 215 GW 2030) — zu bestätigen'),
 (3,'mastr','Marktstammdatenregister','Bundesnetzagentur','https://www.marktstammdatenregister.de',NULL,'DL-DE/BY-2.0',NULL,NULL,NULL,'Anlagenregister PV/Batteriespeicher (georeferenziert)'),
 (4,'builda','ETHOS.BUILDA','FZ Jülich (IEK-3)','https://ethos-builda.fz-juelich.de','10.5281/zenodo.12069755','ODbL','v7_20240429','2026-07-23','1.0.0','Gebäudescharfer Wohngebäudedatensatz DE (NRW=DEA)'),
 (5,'kba','KBA Fahrzeugbestand/-zulassungen','Kraftfahrt-Bundesamt','https://www.kba.de',NULL,NULL,NULL,NULL,NULL,'Pkw-Bestand/Zulassungen nach Antrieb/Region'),
 (6,'bwp','BWP Absatzstatistik Wärmepumpen','Bundesverband Wärmepumpe','https://www.waermepumpe.de',NULL,NULL,NULL,NULL,NULL,'Jährlicher WP-Absatz (Kurvenkalibrierung)'),
 (7,'ffe_wp','FfE Wärmepumpen-Ampel (Potenzial)','Forschungsstelle für Energiewirtschaft (FfE)','https://opendata.ffe.de/dataset/heat-pump-potentials-german-communities/',NULL,'CC-BY-4.0','2022-01-01','2026-08-31','id_opendata=80','Gebäudescharfes WP-Eignungspotenzial DE je Gemeinde/Gebäudetyp/WP-Technologie (Bottom-up-Modell, aggregiert); EFH=internal_id[1]=1, Gesamteignung=internal_id[2]=0'),
 (8,'solarkataster_nrw','Solarkataster NRW','LANUV NRW','https://www.solarkataster.nrw.de',NULL,'dl-de/by-2-0',NULL,NULL,NULL,'Dachflächen-/Ertragspotential PV'),
 (9,'zensus2022','Zensus 2022','Statistische Ämter des Bundes und der Länder','https://www.zensus2022.de',NULL,NULL,'2022',NULL,NULL,'Gebäude/Wohnungen/Heizungsart (aggregiert)'),
 (10,'vg250','Verwaltungsgebiete 1:250 000 (VG250)','Bundesamt für Kartographie und Geodäsie (BKG)','https://gdz.bkg.bund.de',NULL,'dl-de/by-2-0','2025-01-01','2026-07-27','vg250_ebenen_0101','Gemeinde-/Kreisgrenzen DE (Ebene vg250_gem) — räumliche Zuordnung');

-- ============================================================
-- Technologien (Kern + Folge, Kopplung, Substitution)
-- ============================================================
INSERT INTO technologie (id,code,name,typ,basis_code,ist_substitution,beschreibung) VALUES
 (1,'pv','Photovoltaik (Aufdach EFH)','kern',NULL,0,'PV-Aufdachanlage'),
 (2,'ev','Elektrofahrzeug / Heimladepunkt','kern',NULL,1,'BEV mit privatem Ladepunkt; verdrängt Verbrenner'),
 (3,'wp','Wärmepumpe','kern',NULL,1,'WP als Heizsystem; verdrängt Fossilheizung'),
 (4,'batteriespeicher','Stationärer Heimspeicher','folge','pv',0,'PV-Folgetechnologie (Eigenverbrauch)'),
 (5,'waermespeicher','Dezentraler Wärmespeicher','folge','wp',0,'WP-Folgetechnologie (Pufferspeicher), nachrangig');

INSERT INTO kopplung (technologie_id,basis_id,art,beschreibung) VALUES
 (4,1,'hart','Batteriespeicher nur bei EFH mit PV'),
 (5,3,'hart','Wärmespeicher nur bei EFH mit WP');

-- ============================================================
-- Szenarien (Mapping auf T45-Anker)
-- ============================================================
INSERT INTO szenario (id,code,name,referenzpfad,quelle_id,beschreibung) VALUES
 (1,'konservativ','Konservativ','untere Bandbreite',1,'verzögerter Hochlauf; unter T45-Leitpfad'),
 (2,'referenz','Referenz','T45-Strom*',1,'an T45-Leitpfad (T45-Strom*) orientiert'),
 (3,'ambitioniert','Ambitioniert','T45-PV+',1,'beschleunigt; obere T45-Bandbreite (u.a. T45-PV+)');

-- ============================================================
-- Parameter-Katalog
-- ============================================================
INSERT INTO parameter_def (code,name,einheit,gilt_fuer,beschreibung) VALUES
 ('p_max','Sättigungsgrad','Anteil [0..1]','alle','max. Durchdringung unter geeigneten EFH'),
 ('t_m','Wendepunktjahr S-Kurve','Jahr','diffusion','Jahr des Kurvenwendepunkts (P=P_max/2)'),
 ('r','Wachstumsrate (logistisch)','1/a','diffusion','Steilheit der S-Kurve — aus Fit'),
 ('kopplungsquote','Kopplungsquote','Anteil [0..1]','folge','Anteil Basistech-EFH mit Folgetech'),
 ('avg_leistung_kw','Ø installierte Leistung','kW','alle','Ø-Leistung je Objekt (PV: kWp, EV: kW, WP: kW_el)'),
 ('avg_kapazitaet_kwh','Ø Speicherkapazität','kWh','folge','Ø nutzbare Kapazität je Speicher');

-- ============================================================
-- T45/EEG-Zielpfade (national, quellenbelegt)  -> referenzpfad
--   ACHTUNG: nationale Absolutwerte (nicht EFH-Anteile); EFH-Anteil ist abzuleiten.
-- ============================================================
-- PV (installierte Gesamtleistung, GW)
INSERT INTO referenzpfad (pfad,technologie_id,jahr,wert,einheit,quelle_id,kommentar) VALUES
 ('EEG-Ziel', 1,2030,215.0,'GW',2,'gesetzl. Ziel; national gesamt; EFH-Aufdach-Anteil abzuleiten; Wert zu bestätigen'),
 ('T45-Strom*',1,2040,400.0,'GW',1,'national gesamt (EEG-Ziel im T45-Strom*)'),
 ('T45-PV+',  1,2045,693.0,'GW',1,'national gesamt; +30 GW/a ab 2030'),
-- WP (Anlagenbestand Wohngebäude, Mio.)
 ('T45-RedEff',3,2030,8.0,'Mio. Anlagen',1,'inkl. 0,629 Mio. Hybrid-WP; Wohngebäude gesamt'),
 ('T45-Strom', 3,2045,18.6,'Mio. Anlagen',1,'≈ 19,5 − 0,867 Mio. (T45-Strom)'),
 ('T45-RedEff',3,2045,19.5,'Mio. Anlagen',1,'Wohngebäude gesamt'),
-- EV (BEV-Pkw-Bestand, Mio.)
 ('T45-Strom', 2,2030,21.0,'Mio. Fahrzeuge',1,'BEV-Pkw national; auch T45-H2; 2045-Wert noch zu ergänzen'),
-- Batteriespeicher (national gesamt inkl. Großspeicher, GWh)
 ('T45 gesamt',4,2030,125.0,'GWh',1,'national gesamt inkl. Großspeicher; Heimspeicher-Anteil abzuleiten'),
 ('T45 gesamt',4,2045,600.0,'GWh',1,'Bandbreite 500–600 GWh; national gesamt inkl. Großspeicher');

-- ============================================================
-- Szenario-Parameter (ERSTWERTE, T45-verankert; tlw. vorläufig)
-- ============================================================
-- p_max: Anteil GEEIGNETER EFH (nicht T45-Absolutwert!) — Erstwert, nach EFH-Import zu verifizieren
INSERT INTO szenario_parameter (szenario_id,technologie_id,parameter,wert,einheit,quelle_id,kommentar) VALUES
 -- quelle_id NULL: Erstwerte (Sättigungsanteil geeigneter EFH), NICHT aus T45 abgeleitet.
 -- T45 liefert nationale Absolutwerte, keine EFH-Eignungsanteile → Ableitung ausstehend (K1/Partner).
 (1,1,'p_max',0.60,'Anteil',NULL,'Erstwert; Anteil PV-geeigneter EFH; T45-Ableitung ausstehend'),
 (2,1,'p_max',0.75,'Anteil',NULL,'Erstwert; narrativer Anker T45-Strom*; Ableitung ausstehend'),
 (3,1,'p_max',0.90,'Anteil',NULL,'Erstwert; narrativer Anker T45-PV+ (nahe Vollausschöpfung)'),
 (1,2,'p_max',0.70,'Anteil',NULL,'Erstwert; EFH-HH mit BEV+Heimladung; Ableitung ausstehend'),
 (2,2,'p_max',0.85,'Anteil',NULL,'Erstwert; T45-Narrativ Flottenelektrifizierung; Ableitung ausstehend'),
 (3,2,'p_max',0.95,'Anteil',NULL,'Erstwert; obere Bandbreite'),
 (1,3,'p_max',0.65,'Anteil',NULL,'Erstwert; vgl. FfE ~75% EFH WP-geeignet; Ableitung ausstehend'),
 (2,3,'p_max',0.80,'Anteil',NULL,'Erstwert; T45-Narrativ WP dominierend; Ableitung ausstehend'),
 (3,3,'p_max',0.92,'Anteil',NULL,'Erstwert; obere Bandbreite');

-- t_m: Wendepunktjahr (Szenariohebel, VORLÄUFIG — Fit/Abgleich Historie ausstehend)
INSERT INTO szenario_parameter (szenario_id,technologie_id,parameter,wert,einheit,quelle_id,kommentar) VALUES
 (1,1,'t_m',2035,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (2,1,'t_m',2032,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (3,1,'t_m',2030,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (1,2,'t_m',2033,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (2,2,'t_m',2031,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (3,2,'t_m',2029,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (1,3,'t_m',2036,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (2,3,'t_m',2033,'Jahr',NULL,'vorläufig; Fit ausstehend'),
 (3,3,'t_m',2031,'Jahr',NULL,'vorläufig; Fit ausstehend');
-- r (Wachstumsrate): bewusst OFFEN -> aus Kurvenfit an Historie (MaStR/KBA/BWP).

-- kopplungsquote (Folgetechnologien)
INSERT INTO szenario_parameter (szenario_id,technologie_id,parameter,wert,einheit,quelle_id,kommentar) VALUES
 (1,4,'kopplungsquote',0.50,'Anteil',NULL,'Erstwert; Anteil PV-EFH mit Speicher; MaStR-Ableitung ausstehend'),
 (2,4,'kopplungsquote',0.70,'Anteil',NULL,'Erstwert; MaStR-Ableitung ausstehend'),
 (3,4,'kopplungsquote',0.85,'Anteil',NULL,'Erstwert; obere Bandbreite (starke §14a-Anreize)'),
 (1,5,'kopplungsquote',0.70,'Anteil',NULL,'Puffer meist Default; Erstwert Marktannahme'),
 (2,5,'kopplungsquote',0.85,'Anteil',NULL,'Erstwert Marktannahme'),
 (3,5,'kopplungsquote',0.95,'Anteil',NULL,'nahezu Standard');

-- Ø-Größen (szenario-unabhängig; hier unter Referenz gepflegt)
INSERT INTO szenario_parameter (szenario_id,technologie_id,parameter,wert,einheit,quelle_id,kommentar) VALUES
 (2,1,'avg_leistung_kw',10.0,'kWp',NULL,'Erstwert; typ. EFH-PV; MaStR-Ableitung ausstehend'),
 (2,2,'avg_leistung_kw',11.0,'kW',NULL,'Erstwert; Standard-Wallbox'),
 (2,3,'avg_leistung_kw',4.0,'kW',NULL,'Erstwert; el. Anschlussleistung EFH-WP'),
 (2,4,'avg_kapazitaet_kwh',9.0,'kWh',NULL,'Erstwert; typ. Heimspeicher; MaStR-Ableitung ausstehend');

-- Technologieweite Default-Eignungsanteile (Fallback hinter eignung_regional).
-- quelle_id NULL = bewusst unbelegter Erstwert (aus dem Code hierher verlagert; ehrlich markiert).
-- WP wird real je Gemeinde aus FfE (eignung_regional) überschrieben; der Faktor ist nur Fallback.
INSERT INTO eignung_faktor (technologie_id,anteil,quelle_id,kommentar) VALUES
 (1,0.80,NULL,'Erstwert PV-geeignete EFH; datengestützte Ableitung via Solarkataster NRW ausstehend'),
 (3,0.90,NULL,'Fallback WP; real je Gemeinde aus FfE-Ampel (eignung_regional)'),
 (2,0.95,NULL,'Erstwert EV (privater Stellplatz bei EFH); Zensus-/BUILDA-Stellplatz-Proxy ausstehend');
