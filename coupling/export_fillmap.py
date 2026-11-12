"""Export für die 'welche Gebäude füllen sich wann'-Karte.

Pro Szenario×Stützjahr die Pro-Gebäude-PV-Wahrscheinlichkeit (AP2) berechnen, dann mit EINEM
geteilten Zufallsschwellwert je Gebäude zu einem monotonen Füll-Jahr machen (genestete Adoption).
Ausgabe: kompakte Parallel-Arrays als JSON für das Artefakt.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, sqlalchemy

from objecttypegenerator.adapters.parameter_files import (
    load_construction_period_shares, load_design_temperatures, load_technologies, resolve_path)
from objecttypegenerator.adapters.zensus_csv import load_census_tables
from objecttypegenerator.adapters.infdb import InfdbBuildingSource
from objecttypegenerator.application.input_schema import parse_buildings
from objecttypegenerator.application.pipeline import generate_municipality
from objecttypegenerator.application.reference_data import prepare_reference_data
from objecttypegenerator.application.settings import RunSettings, SizingSettings

sys.path.insert(0, "/home/nowum/coding/simuflex/hochlaufszenarien/coupling")
from structure import pv_with_structure  # noqa

AGS = "05374040"
YEARS = [2025, 2030, 2035, 2040, 2045, 2050]
DSN = "postgresql+psycopg2://infdb_user:infdb@127.0.0.1:54328/infdb"
SCEN = json.load(open("/home/nowum/.claude/jobs/55926904/tmp/ap2_scenarios.json"))["szenarien"]
OUT = Path("/home/nowum/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_fillmap.json")

settings = RunSettings(seed=42)
eng = sqlalchemy.create_engine(DSN)
frame = InfdbBuildingSource(eng, input_schema="basedata", heat_loss_schema="ro_heat").load(AGS)
inputs = parse_buildings(frame).by_municipality[AGS]
census = load_census_tables(Path("additional-information"))
techs = load_technologies(resolve_path("package:kfw/kfw_2025.yaml", Path.cwd()))
constr = load_construction_period_shares(resolve_path("package:kfw/construction_period_shares.yaml", Path.cwd()))
design = load_design_temperatures(resolve_path("package:din_en_12831/design_temperatures.csv", Path.cwd()))

oid = list(inputs.objectid)
n = len(oid)
loc = frame.set_index("objectid").reindex(oid)
lon = loc["longitude"].to_numpy(); lat = loc["latitude"].to_numpy()
htype = np.array(inputs.building_type)
ss = SizingSettings()
roof_pot = loc["roof_area_m2"].to_numpy() * ss.pv_roof_usable_fraction * ss.pv_kwp_per_m2

# stabile Größe je Gebäude (geteilt): MaStR-nahe Uniform je Haustyp, auf Dach gedeckelt
rng = np.random.default_rng(1)
is_efh = np.isin(htype, ["SFH", "TH"])
kwp = np.where(is_efh, rng.uniform(3, 10, n), rng.uniform(5, 20, n))
kwp = np.minimum(kwp, np.where(np.isfinite(roof_pot) & (roof_pot > 0), roof_pot, kwp)).round(1)

# geteilter Schwellwert je Gebäude
u = np.random.default_rng(99).random(n)

# Gruppe (owner_share stabil bei festem Seed)
groups = np.array(["MFH"] * n, dtype=object)

fill = {}
for scen in ("konservativ", "referenz", "ambitioniert"):
    crossed = np.zeros(n, dtype=bool)
    fill_year = np.zeros(n, dtype=int)  # 0 = nie
    owner_share_ref = None
    for yr in YEARS:
        rec = SCEN[scen][str(yr)]
        ref = prepare_reference_data(census, pv_with_structure(techs, total=rec["pv_total"], alpha=rec["alpha"]),
                                     constr, design, settings=settings)
        outcome = generate_municipality(inputs, ref, settings)
        p = np.asarray(outcome.draws["pv"].probability, dtype=float)
        if owner_share_ref is None:
            owner_share_ref = np.asarray(outcome.population.owner_share, dtype=float)
        newly = (~crossed) & (p >= u)
        fill_year[newly] = yr
        crossed |= newly
    fill[scen] = fill_year.tolist()
    print(f"{scen}: gefüllt bis 2050 = {int((fill_year>0).sum())}/{n}", file=sys.stderr)

# Gruppen aus owner_share (einmalig, stabil)
groups = np.where(~is_efh, "MFH", np.where(owner_share_ref >= 0.5, "EFH_Eig", "EFH_Miet"))

data = {
    "ags": AGS, "years": YEARS,
    "lon": [round(float(x), 5) for x in lon],
    "lat": [round(float(x), 5) for x in lat],
    "grp": groups.tolist(),
    "kwp": [float(x) for x in kwp],
    "roof_kwp": [round(float(x), 1) if np.isfinite(x) else 0.0 for x in roof_pot],
    "fill": fill,  # je Szenario: Füll-Jahr (0 = nie)
}
OUT.write_text(json.dumps(data, separators=(",", ":")))
print(f"geschrieben: {OUT} ({OUT.stat().st_size//1024} KB, {n} Gebäude)", file=sys.stderr)
