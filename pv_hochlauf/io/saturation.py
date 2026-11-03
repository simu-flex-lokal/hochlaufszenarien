"""
io/saturation.py — Sättigungspotenzial aus ETHOS.BUILDA-Gebäudedaten.

Berechnet für jede Gemeinde das technische PV-Sättigungspotenzial C_hi [kWp].

Hybride Abfragestrategie:
  Kreisfreie Stadt (z.B. Berlin, München, Hamburg)
    → get_footprint_area_statistics(nuts_code=...) [schnell, aggregiert]
  Normale Gemeinde
    → get_residential_buildings(city=...)           [langsam, genau]

Methodik:
  C_hi [kWp] = Σ_Gebäude (footprint_area_m2 × roof_factor × moduleffizienz)

  Dachform-Faktoren (nutzbarer Anteil der Grundfläche):
    flat        → 0.80   Flachdach: optimale Ausrichtung möglich
    gabled      → 0.50   Satteldach: ~eine Seite nutzbar
    hipped      → 0.40   Walmdach
    half_hipped → 0.45
    pyramidal   → 0.35   Zeltdach
    shed        → 0.60   Pultdach
    Fallback    → 0.45   unbekannte Dachform

  Moduleffizienz: 0.205 kWp/m²

  Mindestgröße: nutzbare Dachfläche < MIN_ROOF_AREA_M2 → kein PV-Potenzial

Öffentliche Funktionen:
  fetch_builda_saturation()     : Für eine Gemeinde (hybride Strategie)
  fetch_builda_saturation_bulk(): Für mehrere Gemeinden (parallel)
  build_metadata_df()           : Erstellt metadata_df für compute_saturation()
  saturation_summary()          : Gibt Statistikübersicht aus
"""

from dataclasses import asdict
from typing import Dict, List, Optional, Tuple
from builda_client.client import BuildaClient
from joblib import Parallel, delayed
from tqdm import tqdm

import numpy as np
import pandas as pd
import threading
import shutil

from pv_hochlauf.core.config import BASE_DIR, OUT_PICKLE

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

# Nutzbarer Anteil der Grundfläche je Dachform (nach Quaschning 2021)
ROOF_FACTORS: Dict[str, float] = {
    "shed":         0.69,
    "skillion":     0.69,
    "gabled":       0.49,
    "saltbox":      0.46,
    "sawtooth":     0.46,
    "half-hipped":  0.40,
    "side_hipped":  0.37,
    "flat":         0.35,
    "mansard":      0.35,
    "gambrel":      0.35,
    "hipped":       0.31,
    "many":         0.31,
    "pyramidal":    0.25,
    "round":        0.24,
    "conical":      0.15,
    "cone":         0.15,
    "dome":         0.14,
    "onion":        0.00,
}
#ROOF_FACTOR_DEFAULT = 0.45   # Fallback für unbekannte/fehlende Dachform

# Standard-Moduleffizienz [kWp/m²] (Quelle: Agora Energiewende - Solarstrom vom Dach: das Energiewendepotenzial
#                                       auf Deutschlands Gebäuden)
MODULE_EFFICIENCY_KWP_PER_M2 = 0.205

# Mindest-nutzbare Dachfläche [m²] für PV-Wirtschaftlichkeit (Quelle: Agora Energiewende - Solarstrom vom Dach: 
#                                                           das Energiewendepotenzial auf Deutschlands Gebäuden)
# Gebäude unterhalb dieser Grenze werden nicht berücksichtigt
MIN_ROOF_AREA_M2 = 50.0

BUILDINGS_CACHE_PATH = OUT_PICKLE / "builda_buildings_cache.parquet"
BUILDINGS_CACHE_TMP  = OUT_PICKLE / "builda_buildings_cache.tmp.parquet"

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _extract_value(field) -> Optional[float]:
    """
    Extrahiert den numerischen Wert aus einem BUILDA-Datenfeld.
    BUILDA-Felder sind strukturiert als {'value': ..., 'source': ..., 'lineage': ...}.

    Parameter
    ----------
    field : dict | None

    Returns
    -------
    float | None
    """
    if field is None:
        return None
    if isinstance(field, dict):
        return field.get("value")
    return None


def _extract_str(field) -> Optional[str]:
    """
    Extrahiert den String-Wert aus einem BUILDA-Datenfeld.

    Parameter
    ----------
    field : dict | None

    Returns
    -------
    str | None (lowercase)
    """
    if field is None:
        return None
    if isinstance(field, dict):
        val = field.get("value")
        return str(val).lower() if val is not None else None
    return None


# ---------------------------------------------------------------------------
# Lokaler Cache für Gebäudedaten (footprint_area_m2 + roof_shape)
# ---------------------------------------------------------------------------
# Gespeichert als Parquet-Datei: OUT_PICKLE / "builda_buildings_cache.parquet"
# Spalten: gemeinde_code, footprint_area_m2, roof_shape
# ---------------------------------------------------------------------------

def _load_buildings_cache() -> pd.DataFrame:
    """
    Lädt den lokalen Gebäude-Cache.
    Behandelt fehlende, leere und korrupte Dateien robust.
    """
    empty = pd.DataFrame(columns=["gemeinde_code", "footprint_area_m2", "roof_shape"])

    if not BUILDINGS_CACHE_PATH.exists():
        return empty

    # Datei vorhanden aber leer → löschen und neu starten
    if BUILDINGS_CACHE_PATH.stat().st_size == 0:
        print("  Cache-Datei ist leer (vermutlich unterbrochener Schreibvorgang) "
              "→ wird gelöscht.")
        BUILDINGS_CACHE_PATH.unlink()
        return empty

    try:
        return pd.read_parquet(BUILDINGS_CACHE_PATH)
    except Exception as e:
        print(f"  Cache-Datei korrupt ({e}) → wird gelöscht und neu erstellt.")
        BUILDINGS_CACHE_PATH.unlink()
        return empty


def _save_buildings_cache(df_cache: pd.DataFrame) -> None:
    """
    Speichert den Gebäude-Cache robust (Windows-kompatibel).
    Verwendet thread-eindeutigen tmp-Dateinamen um Konflikte zu vermeiden.
    """
    BUILDINGS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Thread-eindeutiger tmp-Name verhindert Konflikte zwischen parallelen Threads
    thread_id = threading.current_thread().ident
    tmp_path  = BUILDINGS_CACHE_PATH.with_suffix(f".tmp_{thread_id}.parquet")
    
    try:
        df_cache.to_parquet(tmp_path, index=False)
        # shutil.move ist auf Windows robuster als Path.replace
        shutil.move(str(tmp_path), str(BUILDINGS_CACHE_PATH))
    except Exception as e:
        # tmp-Datei aufräumen falls vorhanden
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e


def _fetch_buildings_raw(
    city_code: str,
    client,
    postcodes: Optional[List[str]] = None,
) -> Optional[pd.DataFrame]:
    """
    Ruft Gebäudedaten ab und gibt sie aggregiert nach Dachform zurück.
    
    Statt jedes Gebäude einzeln zu speichern wird die Grundfläche je
    Dachform summiert → deutlich kompaktere Speicherung.
    
    Returns
    -------
    pd.DataFrame  Spalten: [gemeinde_code, roof_shape, footprint_area_m2]
                  Eine Zeile je Dachform (statt eine Zeile je Gebäude)
    """
    buildings: list = []

    for plz in postcodes:
        try:
            resp      = client.get_residential_buildings(nuts_code=city_code, postcode=plz)
            buildings += [asdict(b) for b in resp.buildings]
        except Exception as e:
            print(f"    Gemeinde {city_code}, PLZ {plz}: {type(e).__name__}")
            return None

    if not buildings:
        #print(f"  {city_code}: keine Gebäude gefunden")
        return None

    # Erst in DataFrame, dann nach Dachform aggregieren
    df = pd.DataFrame([{
        "gemeinde_code":     city_code,
        "footprint_area_m2": _extract_value(b.get("footprint_area_m2")) or 0.0,
        "roof_shape":        _extract_str(b.get("roof_shape")),
    } for b in buildings])

    df_agg = (
    df.groupby(["gemeinde_code", "roof_shape"], dropna=False)
    .agg(
            footprint_area_m2=("footprint_area_m2", "sum"),
            building_count=("footprint_area_m2", "size"),  # Anz. Gebäude in Gruppe
        )
        .reset_index()
    )

    return df_agg


def _calc_potential_from_df(
    df_city: pd.DataFrame, 
    roof_factor_default: float,
    ) -> float:
    """
    Berechnet C_hi [kWp] aus einem DataFrame mit Gebäudedaten.
    """
    if df_city.empty:
        return 0.0

    total = 0.0
    for _, row in df_city.iterrows():
        footprint   = float(row["footprint_area_m2"])
        roof_shape  = row.get("roof_shape")
        roof_factor = ROOF_FACTORS.get(roof_shape, roof_factor_default)
        nutzbar     = footprint * roof_factor
        total += nutzbar * MODULE_EFFICIENCY_KWP_PER_M2
    return total

# ---------------------------------------------------------------------------
# Öffentliche Funktionen
# ---------------------------------------------------------------------------

def check_builda_completeness(
    df_cache: pd.DataFrame,
    zensus: pd.DataFrame,
    completeness_threshold: float = 0.7,
) -> pd.DataFrame:
    """
    Prüft für jede Gemeinde im Cache ob die BUILDA-Daten vollständig genug sind.
    
    Vergleicht gefundene Gebäudeanzahl mit Zensus-Sollwert.
    
    Parameter
    ----------
    df_cache               : pd.DataFrame  Cache mit Spalten [gemeinde_code, building_count]
    zensus                 : pd.DataFrame  Index=Gemeindeschluessel, Spalte=Wohngebaeude
    completeness_threshold : float         Mindest-Vollständigkeit (Standard: 80%)
    
    Returns
    -------
    pd.DataFrame  Index=gemeinde_code, Spalten:
                    found_buildings   : int    Gefundene Gebäude in BUILDA
                    expected_buildings: int    Sollwert aus Zensus
                    completeness      : float  Anteil gefundener Gebäude
                    is_complete       : bool   True wenn >= threshold
    """
    # Gebäudeanzahl je Gemeinde aus Cache aggregieren
    found = (
        df_cache.groupby("gemeinde_code")["building_count"]
                .sum()
                .rename("found_buildings")
    )
    
    # Mit Zensus-Sollwerten zusammenführen
    result = found.to_frame()
    result["expected_buildings"] = zensus["Wohngebaeude"].reindex(result.index)
    result["completeness"]       = result["found_buildings"] / result["expected_buildings"]
    result["completeness"]       = result["completeness"].clip(upper=1.0)
    result["is_complete"]        = result["completeness"] >= completeness_threshold
    
    n_complete   = result["is_complete"].sum()
    n_incomplete = (~result["is_complete"]).sum()
    n_no_zensus  = result["expected_buildings"].isna().sum()
    print(f"  Vollständigkeitsprüfung: {n_complete} vollständig, "
          f"{n_incomplete} unvollständig, {n_no_zensus} kein Zensus-Eintrag")
    
    return result


def fetch_builda_saturation_bulk(
    cities: dict,
    n_jobs: int = -1,
) -> Dict[str, float]:
    """
    Berechnet das PV-Sättigungspotenzial für mehrere Gemeinden.

    Kreisfreie Städte werden automatisch schnell über die Statistikmethode
    abgefragt, normale Gemeinden über die Gebäudemethode.
    Die Abfragen laufen parallel (n_jobs=-1 = alle verfügbaren Kerne).

    Parameter
    ----------
    cities  : dict      Gemeindeschluessel → [Gemeindename, Postleitzahl(en)] 
    n_jobs  : int       Parallelisierungsgrad (-1 = alle Kerne)

    Returns
    -------
    dict: Gemeindename → C_hi [kWp]
    """

    # Cache einmal laden
    df_cache = _load_buildings_cache()
    cached_city   = set(df_cache['gemeinde_code'].values)
    city_codes = list(cities.keys())
    missing_city  = [c for c in city_codes if c not in cached_city] #and cities[c]['Gemeinde'] not in KREISFREIE_STAEDTE]

    print(f"BUILDA-Abfrage: {len(cities)} Gemeinden")
    print(f"  Cache-Treffer:   {len(cached_city)}")
    print(f"  API-Abfragen:    {len(missing_city)}")  # +len(stats_city)}, davon Kreisfreie Städte:  {len(stats_city)}")

    # Neue Gebäudedaten nur für fehlende Gemeinden abrufen
    if missing_city:
        # Lock stellt sicher dass nur ein Thread gleichzeitig in den Cache schreibt
        cache_lock = threading.Lock()

        def _worker_fetch_and_save(city: str) -> pd.DataFrame:
            postcodes = cities[city]['Postleitzahl']
            client  = BuildaClient()
            df_city = _fetch_buildings_raw(city, client, postcodes)

            if df_city is not None and not df_city.empty:
                # Lock: nur ein Thread schreibt gleichzeitig
                with cache_lock:
                    # Cache neu laden damit zwischenzeitliche Saves anderer
                    # Threads nicht überschrieben werden
                    df_current = _load_buildings_cache()
                    df_updated = pd.concat([df_current, df_city], ignore_index=True)
                    _save_buildings_cache(df_updated)

            return df_city

        results = Parallel(n_jobs=n_jobs, prefer="threads")(
            delayed(_worker_fetch_and_save)(city)
            for city in tqdm(missing_city, desc="Verarbeite Gemeinden")
        )

        no_response = sum(1 for df in results if df is None or df.empty)
        print(f"{no_response} Gemeinden hatten keinen Treffer")

        # df_cache für die weitere Verarbeitung aktualisieren
        df_cache = _load_buildings_cache()

    # Fallback für unbekannte/fehlende Dachform aus dem Durchschnitt
    # der anderen Gebäude berechnen
    valid_df = df_cache[df_cache["roof_shape"].notna()].copy()
    valid_df["factor"] = valid_df["roof_shape"].map(ROOF_FACTORS)
    roof_factor_default = (
        valid_df["building_count"] * valid_df["factor"]
    ).sum() / valid_df["building_count"].sum()
    
    print(f"Berechneter Fallback: {roof_factor_default}")

    # Potenziale berechnen
    def _worker_calc(city: str) -> Tuple[str, float, str]:
        # city_name = cities[city]['Gemeinde']
        # if city_name in KREISFREIE_STAEDTE:
        #     nuts_code = KREISFREIE_STAEDTE[city_name]
        #     try:
        #         client = BuildaClient()
        #         c_hi = _fetch_via_statistics(nuts_code, client)
        #         method = "statistics"
        #     except Exception:
        #         df_city = df_cache[df_cache['gemeinde_code'] == city]
        #         c_hi = _calc_potential_from_df(df_city)
        #         method = "statistics_fallback"
        # else:
        df_city = df_cache[df_cache['gemeinde_code'] == city]
        c_hi = _calc_potential_from_df(df_city, roof_factor_default)
        method = "cache" if city in cached_city else "buildings"

        return city, c_hi, method

    # Berechnung ausführen (Threads oder Prozesse)
    calc_results = Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(_worker_calc)(city) for city in city_codes
    )

    # 4. Ergebnisse zusammenstellen & Loggen
    results = {}
    for city, c_hi, method in calc_results:
        results[city] = c_hi

    # Zensus-Daten einlesen und formatieren
    zensus = pd.read_csv(
        BASE_DIR / "Daten" / "3000G-1001_de.csv",
        sep=';',
        skiprows=6,  # Überspringt die Metadaten-Kopfzeilen
        skipfooter=3,  # Überspringt die Fußzeilen (Copyright/Stand)
        engine='python',  # Erforderlich für skipfooter
        header=None,
        usecols=[1, 5],  # Spalte 2 (Gemeindeschlüssel) & Spalte 6 (Anzahl Wohngebäude)
        names=['Gemeindeschluessel', 'Wohngebaeude'],
        dtype={'Gemeindeschluessel': str},
        na_values=['.', '-'],  # Behandelt Fehlwerte im Zensus als NaN
        encoding='utf-8-sig',
    )

    # Stellen 6–9 entfernen, um den Gemeindeschlüssel wie im MaStR zu erhalten
    zensus['Gemeindeschluessel'] = (
        zensus['Gemeindeschluessel'].str[:5] + zensus['Gemeindeschluessel'].str[9:]
    )

    # Gemeindeschlüssel als Index setzen
    zensus.set_index('Gemeindeschluessel', inplace=True)

    # Vollständigkeitsprüfung und Anpassung von C_hi
    completeness_df = check_builda_completeness(df_cache, zensus)

    for city_code in list(results.keys()):
        if city_code not in completeness_df.index:
            continue

        row          = completeness_df.loc[city_code]
        completeness = float(row["completeness"]) if not pd.isna(row["completeness"]) else None

        # Kein Zensus-Eintrag → unverändert lassen
        if completeness is None:
            continue

        c_hi = results[city_code]

        if completeness >= 0.8:
            # Ausreichend vollständig → unverändert
            continue

        elif 0.3 <= completeness < 0.8:
            # Teilweise vollständig → hochrechnen
            c_hi_adj            = c_hi / completeness
            results[city_code]  = c_hi_adj

        else:
            # completeness < 0.3 → Daten zu lückenhaft, Fallback auf default_multiplier
            # C_hi wird auf None gesetzt → compute_saturation() greift auf Fallback zurück
            results[city_code] = None

    return results


def build_metadata_df(saturation_data: Dict[str, float]) -> pd.DataFrame:
    """
    Erstellt einen metadata_df aus BUILDA-Sättigungsdaten für compute_saturation().

    Da compute_saturation() intern 'Dachflaeche_m2 × Moduleffizienz' rechnet,
    wird Dachflaeche_m2 = C_hi / MODULE_EFFICIENCY gesetzt, sodass
    compute_saturation() exakt denselben C_hi-Wert reproduziert.

    Parameter
    ----------
    saturation_data : dict  Gemeindeschluessel → C_hi [kWp] (aus fetch_builda_*)

    Returns
    -------
    pd.DataFrame  Index=Gemeindeschluessel,
                  Spalten=[Dachflaeche_m2, Moduleffizienz, C_hi_kWp]
    """
    rows = []
    for city, c_hi_kwp in saturation_data.items():
        # None explizit durchlassen (→ Fallback in compute_saturation)
        if c_hi_kwp is not None and c_hi_kwp > 0:
            implied_area = c_hi_kwp / MODULE_EFFICIENCY_KWP_PER_M2
        else:
            implied_area = None

        rows.append({
            "Gemeinde":       city,
            "Dachflaeche_m2": implied_area,
            "Moduleffizienz": MODULE_EFFICIENCY_KWP_PER_M2,
            "C_hi_kWp":       c_hi_kwp,   # kann None sein
        })

    df = pd.DataFrame(rows).set_index("Gemeinde")
    n_valid   = df["C_hi_kWp"].notna().sum()
    n_fallback = df["C_hi_kWp"].isna().sum()
    print(f"metadata_df: {n_valid} mit BUILDA-Potenzial, "
          f"{n_fallback} mit Fallback (default_multiplier)")
    return df


def saturation_summary(metadata_df: pd.DataFrame) -> None:
    """
    Gibt eine Zusammenfassung der berechneten Sättigungspotenziale aus.

    Parameter
    ----------
    metadata_df : pd.DataFrame  Ausgabe von build_metadata_df()
    """
    print("\n=== PV-Sättigungspotenziale (ETHOS.BUILDA) ===")
    print(f"  Gemeinden:   {len(metadata_df):,}")
    print(f"  Gesamt:      {metadata_df['C_hi_kWp'].sum() / 1e6:.1f} GWp")
    print(f"  Median:      {metadata_df['C_hi_kWp'].median() / 1000:.1f} MWp")
    print(f"  Min:         {metadata_df['C_hi_kWp'].min() / 1000:.1f} MWp")
    print(f"  Max:         {metadata_df['C_hi_kWp'].max() / 1000:.1f} MWp")
    n_zero = (metadata_df["C_hi_kWp"] == 0).sum()
    if n_zero:
        print(f"  Ohne Daten:  {n_zero} Gemeinden (C_hi = 0)")
    print()