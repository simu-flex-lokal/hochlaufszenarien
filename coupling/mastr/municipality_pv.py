#!/usr/bin/env python3
"""PV-Bestand einer Gemeinde im MaStR mit den Filtern von AP 2 — Startwert der Kopplung prüfen.

Gleiche Filter wie ``derive_pv_kwp.py`` (Haushalt, in Betrieb, Gebäudeanlage, ≤ 30 kW). Ausgegeben werden
Anlagenzahl und Leistung zum Ende der KfW-2025-Erhebung (31.03.2025) und zum Stand des MaStR-Abzugs. Die
kalibrierte Kopplung 2025 (``distribute.py``) sollte bei PV-Gebäuden und MWp dazwischen liegen.

    python coupling/mastr/municipality_pv.py 05374040 05374052
"""
import argparse

import psycopg2

DSN = "postgresql://readonly:readonly@timescale.nowum.fh-aachen.de:5432/opendata"
SQL = """
SELECT count(*) FILTER (WHERE "Inbetriebnahmedatum" <= '2025-03-31'),
       sum("Bruttoleistung") FILTER (WHERE "Inbetriebnahmedatum" <= '2025-03-31') / 1000,
       count(*), sum("Bruttoleistung") / 1000, max("DatumDownload")
FROM "mastr-2025".solar_extended
WHERE "Gemeindeschluessel" = %(ags)s
  AND "Nutzungsbereich" = 'Haushalt'
  AND "EinheitBetriebsstatus" = 'In Betrieb'
  AND ("ArtDerSolaranlage" LIKE '%%Hausdach%%' OR "ArtDerSolaranlage" LIKE '%%Gebäude%%')
  AND "Bruttoleistung" <= 30
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ags", nargs="+", help="Amtlicher Gemeindeschlüssel (8-stellig)")
    args = parser.parse_args()
    with psycopg2.connect(DSN) as connection, connection.cursor() as cursor:
        for ags in args.ags:
            cursor.execute(SQL, {"ags": ags})
            n_q1, mwp_q1, n_all, mwp_all, download = cursor.fetchone()
            print(f"{ags}: bis 31.03.2025 {n_q1} Anlagen, {mwp_q1 or 0:.2f} MWp | "
                  f"bis Abzug ({download}) {n_all} Anlagen, {mwp_all or 0:.2f} MWp")


if __name__ == "__main__":
    main()
