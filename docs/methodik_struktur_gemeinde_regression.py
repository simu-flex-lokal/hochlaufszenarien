"""Machbarkeit: gruppenspezifische PV-Durchdringung (Gebäudeebene) aus MaStR × Zensus 2022, Gemeinde-Querschnitt je Jahr."""
# Machbarkeitsprüfung zu docs/methodik_struktur_vorschlag.md, Abschnitt 2.4 (Ergebnis: nicht belastbar). Erwartet mastr_gem_year.csv (ags, yr, cls, n, kw) in $CLAUDE_JOB_DIR/tmp/emp; im ObjectTypeGenerator-Verzeichnis ausführen.
import os
from pathlib import Path
import numpy as np, pandas as pd
from objecttypegenerator.adapters.zensus_csv import load_census_tables

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp/emp"
ct = load_census_tables(Path("additional-information"))
hs, ow, bf = ct.household_sizes, ct.ownership, ct.building_forms
hh = pd.DataFrame(np.nansum(hs.counts, axis=2), index=list(hs.municipalities.ags), columns=["c1", "c2", "c3_6", "c7_12", "c13"])
q = pd.DataFrame(ow.quotes, index=list(ow.municipalities.ags))
land = dict(zip(ow.land_codes, ow.land_quotes))
def fill(row):  # fehlende Quoten (geheim) durch Landeswert
    lq = land.get(row.name[:2]);  return row.fillna(pd.Series(lq, index=row.index)) if lq is not None else row
q = q.apply(fill, axis=1)
qq = pd.DataFrame({"q1": q[[0, 1, 2]].mean(axis=1), "q2": q[[3, 4, 5]].mean(axis=1)}, index=q.index)
b = pd.DataFrame(np.nansum(bf.counts, axis=1), index=list(bf.municipalities.ags), columns=["bld"])
z = hh.join(qq, how="inner").join(b, how="inner")
z = z[~z.index.duplicated()]
efh_o = z.c1 * z.q1 + z.c2 * z.q2               # selbstgenutzte EFH/ZFH (≈ ein Eigentümerhaushalt je Gebäude)
efh_all = z.c1 + z.c2 / 2
efh_t = (efh_all - efh_o).clip(lower=0)
mfh = (z.bld - efh_all).clip(lower=0)
S = pd.DataFrame({"EO": efh_o, "ET": efh_t, "M": mfh, "pop_hh": hh.sum(axis=1)}).dropna()
S = S[(S[["EO", "ET", "M"]].sum(axis=1) > 50)]
S["B"] = S[["EO", "ET", "M"]].sum(axis=1)

m = pd.read_csv(T / "mastr_gem_year.csv", dtype={"ags": str})
m = m[m.cls == "r1_30"].groupby(["ags", "yr"]).n.sum().unstack(fill_value=0).sort_index(axis=1).cumsum(axis=1)
D = S.join(m, how="inner")
print("Gemeinden:", len(D), " davon NRW:", D.index.str.startswith("05").sum())
# Gemeindetyp nach Haushalten (Proxy Einwohner ~ 2 je HH): <2.5k HH, <10k, <50k, ≥50k
gt = pd.cut(D.pop_hh * 2, [0, 5e3, 2e4, 1e5, 1e9], labels=["Land", "Klein", "Mittel", "Gross"])
dummies = pd.get_dummies(D.index.str[:2], prefix="L", drop_first=False).set_index(D.index).astype(float)
gtd = pd.get_dummies(gt, prefix="T").set_index(D.index).astype(float)
shares = D[["EO", "ET", "M"]].div(D.B, axis=0)

def fit(years, sel, controls):
    rows = []
    for yr in years:
        y = D.loc[sel, yr] / D.loc[sel, "B"]
        X = shares.loc[sel].copy()
        if controls:
            Xl = dummies.loc[sel].drop(columns=[c for c in dummies if c == "L_05" or dummies.loc[sel, c].sum() == 0])
            Xt = gtd.loc[sel].drop(columns=["T_Land"])
            X = pd.concat([X, Xl, Xt], axis=1)
        w = D.loc[sel, "B"].to_numpy()
        Xa, ya = X.to_numpy() * np.sqrt(w)[:, None], y.to_numpy() * np.sqrt(w)
        coef, *_ = np.linalg.lstsq(Xa, ya, rcond=None)
        res = ya - Xa @ coef
        cov = np.linalg.pinv(Xa.T @ Xa) * (res @ res) / (len(ya) - X.shape[1])
        se = np.sqrt(np.diag(cov))
        rows.append({"yr": yr, **{k: coef[i] for i, k in enumerate(["EO", "ET", "M"])},
                     **{f"se_{k}": se[i] for i, k in enumerate(["EO", "ET", "M"])}})
    r = pd.DataFrame(rows).set_index("yr")
    r["ET/EO"] = r.ET / r.EO; r["M/EO"] = r.M / r.EO
    return r

years = [2012, 2015, 2018, 2020, 2021, 2022, 2023, 2024, 2025]
nrw = D.index.str.startswith("05")
pd.set_option("display.width", 200); pd.set_option("display.precision", 3)
for name, sel, ctl in [("DE, Land+Gemeindetyp-Kontrollen (Ref. NRW, Landgemeinde)", np.ones(len(D), bool), True),
                       ("DE, ohne Kontrollen", np.ones(len(D), bool), False),
                       ("NRW, Gemeindetyp-Kontrollen", nrw, True)]:
    print("\n==", name); r = fit(years, sel, ctl); print(r.round(3)); r.to_csv(T / f"fit_{name[:3].strip(',')}_{int(ctl)}.csv")
