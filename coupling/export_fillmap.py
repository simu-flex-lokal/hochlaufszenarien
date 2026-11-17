"""Export für die Karte "welche Gebäude füllen sich wann".

Je Szenario × Stützjahr die PV-Wahrscheinlichkeit je Gebäude aus AP 2 (mit Struktur-Konvergenz aus
``distribute.py``), dann mit EINEM geteilten Zufallsschwellwert je Gebäude ein monotones Füll-Jahr (genestete
Adoption: wer einmal PV hat, behält sie). Wie in AP 2 bekommen Gebäude ohne geeignetes Dach (Solarkataster: 0 kWp)
keine PV, die übrigen werden so hochskaliert, dass die erwartete Zahl gleich bleibt.

Anlagengröße je Gebäude: einmal für alle Gebäude, die in irgendeinem Szenario PV bekommen, mit AP 2 gezogen
(MaStR-Verteilung, nach Größenklassen auf das Dachpotenzial gelegt) und über die Jahre fest.

Ausführen aus dem ObjectTypeGenerator-Verzeichnis (dessen venv hat AP 2), nach ``distribute.py``:
    cd ~/coding/simuflex/hochlauf/objekttypegenerator
    uv run python ~/coding/simuflex/hochlaufszenarien/coupling/export_fillmap.py \\
        --scenarios ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_ap2_scenarios.json \\
        --out ~/coding/simuflex/hochlaufszenarien/notebooks/data/reichshof_fillmap.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from objecttypegenerator.application.input_schema import parse_buildings
from objecttypegenerator.application.pipeline import generate_municipality
from objecttypegenerator.application.reference_data import prepare_reference_data
from objecttypegenerator.application.technology_sizing import roof_pv_potential_kwp, without_suitable_roof
from objecttypegenerator.domain.categories import house_type_of
from objecttypegenerator.domain.sizing import size_pv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from distribute import load_inputs  # noqa: E402
from structure import pv_with_structure  # noqa: E402

SCENARIOS = ("konservativ", "referenz", "ambitioniert")


def pv_probability(inputs, reference, settings, allowed) -> tuple[np.ndarray, np.ndarray]:
    """Wahrscheinlichkeit je Gebäude wie im AP-2-Zug (inkl. Dach-Ausschluss) und Eigentümeranteil."""
    outcome = generate_municipality(inputs, reference, settings)
    p = np.asarray(outcome.draws["pv"].probability, dtype=float)
    scale = p.sum() / p[allowed].sum()
    return np.where(allowed, np.minimum(p * scale, 1.0), 0.0), np.asarray(outcome.population.owner_share)


def export(scenarios_json: str, ags: str, dsn: str, out: str) -> None:
    scenarios = json.loads(Path(scenarios_json).read_text())["szenarien"]
    settings, frame, (census, techs, constr, design), _ = load_inputs(dsn, ags)
    inputs = parse_buildings(frame).by_municipality[ags]
    n = len(inputs)
    allowed = ~without_suitable_roof(inputs)
    roof = roof_pv_potential_kwp(inputs, settings.sizing)
    threshold = np.random.default_rng(99).random(n)  # geteilter Schwellwert je Gebäude

    fill, owner_share = {}, None
    for scenario in SCENARIOS:
        fill_year = np.zeros(n, dtype=int)  # 0 = nie
        for year, rec in sorted(scenarios[scenario].items(), key=lambda kv: int(kv[0])):
            reference = prepare_reference_data(
                census, pv_with_structure(techs, total=rec["pv_total"], alpha=rec["alpha"]), constr, design,
                settings=settings)
            p, owner = pv_probability(inputs, reference, settings, allowed)
            owner_share = owner if owner_share is None else owner_share
            fill_year[(fill_year == 0) & (p >= threshold)] = int(year)
        fill[scenario] = fill_year
        print(f"{scenario}: bis 2050 {int((fill_year > 0).sum())}/{n} Gebäude", file=sys.stderr)

    house_types = house_type_of(inputs.building_type)
    ever = np.any(np.stack([f > 0 for f in fill.values()]), axis=0)
    kwp = size_pv(ever, house_types, settings.sizing.pv_kwp, rng=np.random.default_rng(1), max_kwp=roof,
                  class_edges_kwp=settings.sizing.pv_size_classes_kwp)

    is_efh = np.isin(np.array(inputs.building_type), ["SFH", "TH"])
    groups = np.where(~is_efh, "MFH", np.where(owner_share >= 0.5, "EFH_Eig", "EFH_Miet"))
    for scenario, fill_year in fill.items():
        for year in (2025, 2050):
            sel = (fill_year > 0) & (fill_year <= year)
            print(f"  {scenario} {year}: {sel.sum()} Gebäude, {np.nansum(kwp[sel]) / 1e3:.1f} MWp "
                  f"(Ziel {scenarios[scenario][str(year)]['ziel_mwp']})", file=sys.stderr)

    data = {
        "ags": ags,
        "years": sorted(int(y) for y in scenarios["referenz"]),
        "lon": [round(float(x), 5) for x in inputs.longitude],
        "lat": [round(float(x), 5) for x in inputs.latitude],
        "grp": groups.tolist(),
        "kwp": [round(float(x), 1) if np.isfinite(x) else 0.0 for x in kwp],
        "roof_kwp": [round(float(x), 1) if np.isfinite(x) else 0.0 for x in roof],
        "fill": {scenario: f.tolist() for scenario, f in fill.items()},  # Füll-Jahr je Gebäude, 0 = nie
    }
    Path(out).write_text(json.dumps(data, separators=(",", ":")))
    print(f"geschrieben: {out} ({Path(out).stat().st_size // 1024} KB, {n} Gebäude)", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", required=True, help="Ergebnis von distribute.py (JSON)")
    parser.add_argument("--ags", default="05374040")
    parser.add_argument("--dsn", default="postgresql+psycopg2://infdb_user:infdb@127.0.0.1:54338/infdb")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    export(args.scenarios, args.ags, args.dsn, args.out)


if __name__ == "__main__":
    main()
