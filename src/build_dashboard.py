"""Genera ``dashboard/index.html``: un único HTML autocontenido con los datos embebidos.

Uso::

    python -m src.build_dashboard

Todo el cálculo se hace en :mod:`src.analytics` (el mismo código que usa el notebook);
aquí solo se serializa a JSON y se inyecta, junto con ``dashboard.js``, en la plantilla
``src/templates/dashboard.html``.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import pandas as pd

from . import analytics as A
from .catalog import BLOCKS, LEGISLATURES, SERIES, SPEC_BY_KEY, XIV_START, XV_START

TEMPLATE = A.ROOT / "src" / "templates" / "dashboard.html"
SCRIPT = A.ROOT / "src" / "templates" / "dashboard.js"
OUT = A.ROOT / "dashboard" / "index.html"


# ─── Serialización ──────────────────────────────────────────────────────────
def ms(ts) -> int:
    return int(pd.Timestamp(ts).timestamp() * 1000)


def num(v, nd: int = 3):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, nd)


def pts(s: pd.Series, nd: int = 3) -> list[list]:
    return [[ms(i), num(v, nd)] for i, v in s.dropna().items()]


def year_pts(s: pd.Series, nd: int = 3) -> list[list]:
    return [[int(i), num(v, nd)] for i, v in s.dropna().items()]


def latest_by_dim(key: str, exclude: tuple[str, ...] = ()) -> dict:
    w = A.wide(key)
    last = w.ffill().iloc[-1]
    return {
        "date": A.period_label(w.dropna(how="all").index[-1], SPEC_BY_KEY[key].freq),
        "values": {d: num(v) for d, v in last.items() if d not in exclude and not pd.isna(v)},
    }


# ─── Bloques del payload ────────────────────────────────────────────────────
def build_kpis() -> list[dict]:
    sc = A.scorecard()
    out = []
    for _, r in sc.iterrows():
        s = A.series(r.key)
        hist = s[s.index >= "2014-01-01"]
        z = r.delta / hist.std() if r.delta is not None and hist.std() else None
        if z is not None and r.better == "down":
            z = -z
        out.append({
            "key": r.key, "label": r.label, "block": r.block, "block_name": r.block_name,
            "unit": r.unit, "freq": r.freq, "better": r.better,
            "latest": num(r.latest), "latest_label": r.latest_label,
            "start": num(r.start), "start_label": r.start_label,
            "delta": num(r.delta), "delta_pct": num(r.delta_pct, 2),
            "improved": None if pd.isna(r.improved) else bool(r.improved),
            "xiv_delta": num(r.xiv_delta), "z": num(z, 2),
            "desc": SPEC_BY_KEY[r.key].desc,
            "spark": pts(s[s.index >= "2019-01-01"]),
        })
    return out


def build_series() -> dict:
    return {s.key: pts(A.series(s.key)) for s in SERIES if s.multi is None}


def build_meta() -> dict:
    df, cat = A.load_long(), A.load_catalog()
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "xv_start": XV_START, "xiv_start": XIV_START,
        "xv_ms": ms(XV_START), "xiv_ms": ms(XIV_START),
        "legislatures": [{**leg, "ms": ms(leg["start"])} for leg in LEGISLATURES],
        "n_obs": int(len(df)), "n_series": int(df.groupby(["key", "dim"]).ngroups),
        "n_tables": int(cat["table"].nunique()), "n_indicators": int(len(cat)),
        "first": str(df["fecha"].min().date()), "last": str(df["fecha"].max().date()),
        "blocks": BLOCKS,
    }


def build_sources() -> list[dict]:
    cat = A.load_catalog()
    rows = []
    for table, g in cat.groupby("table"):
        rows.append({
            "table": int(table), "url": g["table_url"].iloc[0], "source": g["source"].iloc[0],
            "block": BLOCKS.get(g["block"].iloc[0], g["block"].iloc[0]),
            "indicators": g["label"].tolist(), "freq": g["freq"].iloc[0],
            "first": str(g["first"].min())[:7], "last": str(g["last"].max())[:7],
            "n_series": int(g["n_series"].sum()),
        })
    return sorted(rows, key=lambda r: (r["block"], r["table"]))


def build_empleo() -> dict:
    w = A.wide("ocupados_sector")
    start = w[w.index <= A.XV].iloc[-1]
    last = w.iloc[-1]
    aggregates = {"Total CNAE", "Total Nacional", "Servicios", "Industria manufacturera"}
    sector = sorted(
        [{"name": d, "pct": num((last[d] / start[d] - 1) * 100, 2), "abs": num(last[d] - start[d], 1)}
         for d in w.columns if start[d] and d not in aggregates],
        key=lambda r: r["pct"],
    )
    total = w["Total CNAE"] if "Total CNAE" in w else w.drop(columns=list(aggregates), errors="ignore").sum(axis=1)
    qp = A.quarterly_panel()
    bev = qp[["paro", "vacantes", "legislatura"]].dropna()
    prod = A.wide("productividad")
    ld = A.wide("paro_ld_edad")
    return {
        "sector": sector, "sector_total": num((total.iloc[-1] / total[total.index <= A.XV].iloc[-1] - 1) * 100, 2),
        "sector_since": A.period_label(w[w.index <= A.XV].index[-1], "Q"),
        "sector_to": A.period_label(w.index[-1], "Q"),
        "beveridge": [{"x": num(r.paro, 2), "y": num(r.vacantes, 0), "leg": r.legislatura,
                       "label": A.period_label(i, "Q")} for i, r in bev.iterrows()],
        "productividad": {d: pts(prod[d]) for d in prod.columns},
        "paro_ld": {d: pts(ld[d]) for d in ld.columns},
    }


def build_precios() -> dict:
    w = A.wide("ipc_grupos")
    w = w[w.index.year >= 2015]
    annual = w.groupby(w.index.year).mean().round(1)
    return {
        "grupos": latest_by_dim("ipc_grupos"),
        "ccaa": latest_by_dim("ipc_ccaa", exclude=("España",)),
        "heat": {"years": [int(y) for y in annual.index], "groups": list(annual.columns),
                 "values": [[num(v, 1) for v in annual[c]] for c in annual.columns]},
    }


def build_salarios() -> dict:
    rw = A.real_wages()
    dist = pd.concat({k: A.series(f"salario_{k}") for k in ("p10", "mediana", "medio", "p90")}, axis=1).dropna()
    dist_idx = dist / dist.iloc[0] * 100
    return {
        "nominal_idx": pts(rw["nominal_idx"]), "ipc_idx": pts(rw["ipc_idx"]), "real_idx": pts(rw["real_idx"]),
        "real_yoy": pts(rw["real_yoy"]), "nominal_yoy": pts(rw["nominal_yoy"]), "ipc_yoy": pts(rw["ipc_yoy"]),
        "dist": {k: pts(dist[k], 0) for k in dist.columns},
        "dist_idx": {k: pts(dist_idx[k], 2) for k in dist.columns},
        "dist_base": int(dist.index[0].year),
        "p90p10": pts((dist["p90"] / dist["p10"]).round(3)),
    }


def _gap_rows(df: pd.DataFrame) -> list[dict]:
    return [{"name": i, "h": num(r.hombres, 2), "m": num(r.mujeres, 2), "gap": num(r.brecha, 2)} for i, r in df.iterrows()]


def build_genero() -> dict:
    gg = A.gender_gap()
    occ, act, sec = (A.gender_gap_by(p) for p in ("salario_ocupacion", "salario_actividad", "salario_hora_sector"))
    lab = A.labour_gender()
    ccaa = A.gender_gap_ccaa().drop(index=["España"], errors="ignore").sort_values()
    return {
        "gap": {c: pts(gg[c]) for c in gg.columns},
        "occupation": _gap_rows(occ.drop(index=[i for i in occ.index if i.startswith("Todas")])),
        "activity": _gap_rows(act.drop(index=[i for i in act.index if i.startswith("Todas")])),
        "sector_hour": _gap_rows(sec), "year": occ.attrs["year"],
        "ccaa": [{"name": i, "gap": num(v, 2)} for i, v in ccaa.items()],
        "ccaa_spain": num(A.gender_gap_ccaa().get("España"), 2),
        "paro_gap": pts(lab["brecha_paro_pp"].dropna()),
        "salario_h": pts(A.series("salario_hombres"), 0), "salario_m": pts(A.series("salario_mujeres"), 0),
        "hora_h": pts(A.series("salario_hora_hombres"), 2), "hora_m": pts(A.series("salario_hora_mujeres"), 2),
    }


def build_justicia() -> dict:
    cr = A.conviction_rates()
    years = sorted(cr["anyo"].unique())
    by = {nat: cr[cr["nacionalidad"] == nat].set_index("anyo") for nat in ("total", "española", "extranjera")}
    last = int(cr["anyo"].max())
    ast = A.age_structure()
    ct = A.crimes_by_type()
    share = A.foreign_adult_share()
    sex = A.conviction_sex_share()
    last_rates = cr[cr["anyo"] == last].set_index("nacionalidad")
    return {
        "years": [int(y) for y in years], "last": last,
        "rates": {nat: {m: [num(by[nat].loc[y, m], 3) for y in years]
                        for m in ("tasa_bruta", "tasa_edad", "tasa_edad_sexo", "condenados", "poblacion_18")}
                  for nat in by},
        "ratios": {m: [num(by["extranjera"].loc[y, m], 3) for y in years] for m in ("ratio_bruta", "ratio_edad", "ratio_edad_sexo")},
        "bands": [b.replace("De ", "").replace(" años", "").replace(" y más", "+") for b in A.CONDENA_BANDS],
        "age_structure": {nat: [num(v, 2) for v in ast[nat]] for nat in ast.columns}, "age_year": ast.attrs["year"],
        "age_rates": {nat: [num(last_rates.loc[nat, f"tasa_{b}"], 2) for b in A.CONDENA_BANDS] for nat in ("española", "extranjera")},
        "types": [{"name": i, "total": num(r.total, 0), "pct": num(r.pct_extranjera, 2)} for i, r in ct.iterrows()],
        "types_year": ct.attrs["year"],
        "foreign_share": year_pts(share), "foreign_share_ref": num(share.get(ct.attrs["year"]), 2),
        "men_share": {c: year_pts(sex[c]) for c in sex.columns},
    }


def build_demografia() -> dict:
    pop = A.population_by_nationality()
    tot = pop[pop["nacionalidad"] == "total"]["Todas las edades"]
    ext = pop[pop["nacionalidad"] == "extranjera"]["Todas las edades"]
    tw, ew = A.wide("pob_sexo_edad_total"), A.wide("pob_sexo_edad_espanola")
    t_last, e_last = tw.iloc[-1], ew.iloc[-1]
    groups = sorted({c.rsplit(". ", 1)[0] for c in tw.columns}, key=lambda g: A._age_bounds(g)[0])
    pyramid = []
    for g in groups:
        row = {"group": g.replace("De ", "").replace(" años", "").replace(" y más", "+")}
        for sexo in ("Hombres", "Mujeres"):
            t, e = t_last.get(f"{g}. {sexo}"), e_last.get(f"{g}. {sexo}")
            row[f"{sexo}_esp"], row[f"{sexo}_ext"] = num(e, 0), num(t - e, 0)
        pyramid.append(row)
    return {
        "pop": year_pts(tot / 1e6, 3), "foreign_pct": year_pts(ext / tot * 100, 2),
        "pyramid": pyramid, "pyramid_date": A.period_label(tw.index[-1], "S"),
    }


def build_territorio() -> dict:
    t = A.ccaa_table()
    sig = A.sigma_convergence()
    rows = [{"name": i, **{c: num(v, 2) for c, v in r.items()}} for i, r in t.iterrows()]
    return {"rows": rows, "sigma": pts(sig)}


def build_macro() -> dict:
    qp = A.quarterly_panel()
    ph = qp[["paro", "ipc_subyacente", "legislatura"]].dropna()
    mis = qp["indice_miseria"].dropna()
    mis_leg = qp.groupby("legislatura")["indice_miseria"].mean()
    events = {}
    for key, (mode, label) in A.EVENT_KEYS.items():
        ev = A.event_study(key, mode)
        events[key] = {"label": label, "mode": mode,
                       **{leg: [[int(r.mes), num(r.valor, 2)] for r in g.itertuples()] for leg, g in ev.groupby("legislatura")}}
    corr = A.correlation_matrix()
    return {
        "phillips": [{"x": num(r.paro, 2), "y": num(r.ipc_subyacente, 2), "leg": r.legislatura,
                      "label": A.period_label(i, "Q")} for i, r in ph.iterrows()],
        "misery": pts(mis, 2), "misery_leg": {k: num(v, 2) for k, v in mis_leg.items()},
        "events": events,
        "corr": {"labels": list(corr.columns), "values": corr.values.tolist()},
        "flows": {c: pts(s.dropna(), 0) for c, s in A.flows_12m().items()},
        "esfuerzo": {c: pts(A.housing_affordability()[c].dropna(), 2) for c in ("ipv_idx", "salario_idx", "esfuerzo", "alquiler_idx")},
        "ipv_ccaa": latest_by_dim("ipv_ccaa", exclude=("España",)),
        "arope_ccaa": latest_by_dim("arope_ccaa", exclude=("España",)),
    }


def build_payload() -> dict:
    return {
        "meta": build_meta(), "kpis": build_kpis(), "s": build_series(),
        "units": {s.key: s.unit for s in SERIES}, "labels": {s.key: s.label for s in SERIES},
        "insights": A.insights(), "sources": build_sources(),
        "empleo": build_empleo(), "precios": build_precios(), "salarios": build_salarios(),
        "genero": build_genero(), "justicia": build_justicia(), "demografia": build_demografia(),
        "territorio": build_territorio(), "macro": build_macro(),
    }


def main() -> None:
    payload = build_payload()
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = SCRIPT.read_text(encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__SCRIPT__", script).replace("__PAYLOAD__", data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard escrito en {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
