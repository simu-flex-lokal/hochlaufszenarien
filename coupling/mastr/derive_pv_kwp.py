#!/usr/bin/env python3
"""Größenverteilung von Dach-PV-Anlagen der Haushalte aus dem MaStR (OEDS) als AP-2-Quantildatei.

Gleiche Filter wie ``objecttypegenerator derive-mastr`` (AP 2, ``adapters/mastr_derive.py``): Haushalt,
in Betrieb, Gebäudeanlage, ≤ 30 kW, in Betrieb genommen bis 31.03.2025 (Ende der KfW-2025-Erhebung).
AP 2 liest daraus ``mastr_pv_kwp.csv`` (1.001 Quantile, Spalten ``level,value``) statt der Ersatzgrößen
(EFH 3–10 kWp, MFH 5–20 kWp). Quelle hier ist der MaStR-Abzug im OEDS statt des open-mastr-Downloads.

    python coupling/mastr/derive_pv_kwp.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

DSN = "postgresql://readonly:readonly@timescale.nowum.fh-aachen.de:5432/opendata"
OUT = Path(__file__).resolve().parent / "mastr_pv_kwp.csv"
LEVELS = np.linspace(0.0, 1.0, 1001)

SQL = """
SELECT count(*), avg("Bruttoleistung"),
       percentile_cont(%(levels)s::float8[]) WITHIN GROUP (ORDER BY "Bruttoleistung")
FROM "mastr-2025".solar_extended
WHERE "Nutzungsbereich" = 'Haushalt'
  AND "EinheitBetriebsstatus" = 'In Betrieb'
  AND ("ArtDerSolaranlage" LIKE '%%Hausdach%%' OR "ArtDerSolaranlage" LIKE '%%Gebäude%%')
  AND "Bruttoleistung" <= 30
  AND "Inbetriebnahmedatum" <= '2025-03-31'
"""


def main() -> None:
    with psycopg2.connect(DSN) as connection, connection.cursor() as cursor:
        cursor.execute(SQL, {"levels": LEVELS.tolist()})
        count, mean, quantiles = cursor.fetchone()
    pd.DataFrame({"level": LEVELS, "value": quantiles}).to_csv(OUT, index=False)
    print(f"{count} Anlagen, Ø {mean:.2f} kWp → {OUT}")


if __name__ == "__main__":
    main()
