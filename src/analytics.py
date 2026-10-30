"""Capa analítica compartida por el notebook y el dashboard.

Todas las funciones trabajan sobre ``data/processed/series_long.csv`` y devuelven
objetos pandas, de modo que el EDA y el dashboard calculan exactamente lo mismo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .catalog import BLOCKS, LEGISLATURES, SPEC_BY_KEY, XIV_START, XV_START

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"

XV = pd.Timestamp(XV_START)
XIV = pd.Timestamp(XIV_START)
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ─── Carga ──────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_long() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "series_long.csv", dtype={"dim": "string", "periodo": "string"})
    df["dim"] = df["dim"].fillna("")
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


@lru_cache(maxsize=1)
def load_catalog() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "catalog.csv")


def series(key: str, dim: str = "") -> pd.Series:
    df = load_long()
    sub = df[(df["key"] == key) & (df["dim"] == dim)]
    s = sub.set_index("fecha")["valor"].sort_index()
    s.name = key if not dim else f"{key}:{dim}"
    return s


def wide(key: str) -> pd.DataFrame:
    df = load_long()
    sub = df[df["key"] == key]
    return sub.pivot_table(index="fecha", columns="dim", values="valor").sort_index()


def period_label(fecha: pd.Timestamp, freq: str) -> str:
    if freq == "M":
        return f"{MESES[fecha.month - 1]} {fecha.year}"
    if freq == "Q":
        return f"T{(fecha.month - 1) // 3 + 1} {fecha.year}"
    if freq == "S":
        return f"{fecha.day} {MESES[fecha.month - 1]} {fecha.year}"
    return str(fecha.year)


def to_quarterly(s: pd.Series, how: str = "mean") -> pd.Series:
    q = s.resample("QS").agg(how)
    return q.dropna()


def rolling_12m(s: pd.Series) -> pd.Series:
    """Suma móvil de 12 meses (elimina estacionalidad en flujos mensuales)."""
    return s.rolling(12, min_periods=12).sum().dropna()


def value_at(s: pd.Series, when: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    """Último dato publicado con periodo de referencia ≤ ``when``."""
    s = s.dropna()
    before = s[s.index <= when]
    if before.empty:
        return None
    return before.index[-1], float(before.iloc[-1])


# ─── Scorecard ──────────────────────────────────────────────────────────────
SCORECARD_KEYS = [
    "paro", "paro_juvenil", "empleo", "ocupados", "temporalidad",
    "ipc", "ipc_subyacente", "pib", "ipi",
    "coste_salarial", "salario_mediana",
    "ipv", "tipo_hipoteca",
    "arope", "carencia_severa", "gini",
]


@dataclass
class Kpi:
    key: str
    label: str
    block: str
    unit: str
    freq: str
    better: str | None
    latest: float
    latest_date: pd.Timestamp
    start: float | None
    start_date: pd.Timestamp | None
    delta: float | None
    delta_pct: float | None
    improved: bool | None
    xiv_delta: float | None

    @property
    def latest_label(self) -> str:
        return period_label(self.latest_date, self.freq)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["latest_label"] = period_label(self.latest_date, self.freq)
        d["start_label"] = period_label(self.start_date, self.freq) if self.start_date is not None else None
        d["latest_date"] = self.latest_date.date().isoformat()
        d["start_date"] = self.start_date.date().isoformat() if self.start_date is not None else None
        return d


def kpi(key: str, dim: str = "") -> Kpi | None:
    spec = SPEC_BY_KEY[key]
    s = series(key, dim).dropna()
    if s.empty:
        return None
    start = value_at(s, XV)
    xiv_start, xiv_end = value_at(s, XIV), start
    delta = delta_pct = improved = xiv_delta = None
    if start:
        delta = float(s.iloc[-1] - start[1])
        delta_pct = float(delta / abs(start[1]) * 100) if start[1] else None
        if spec.better and abs(delta) > 1e-9:
            improved = (delta < 0) if spec.better == "down" else (delta > 0)
    if xiv_start and xiv_end:
        xiv_delta = float(xiv_end[1] - xiv_start[1])
    return Kpi(
        key=key, label=spec.label, block=spec.block, unit=spec.unit, freq=spec.freq, better=spec.better,
        latest=float(s.iloc[-1]), latest_date=s.index[-1],
        start=start[1] if start else None, start_date=start[0] if start else None,
        delta=delta, delta_pct=delta_pct, improved=improved, xiv_delta=xiv_delta,
    )


def scorecard(keys: list[str] | None = None) -> pd.DataFrame:
    rows = [k.as_dict() for key in (keys or SCORECARD_KEYS) if (k := kpi(key))]
    df = pd.DataFrame(rows)
    df["block_name"] = df["block"].map(BLOCKS)
    return df


# ─── Comparativa entre legislaturas (event study) ───────────────────────────
EVENT_KEYS = {
    "paro": ("level", "Tasa de paro (%)"),
    "ocupados": ("index", "Ocupados EPA (base 100 = investidura)"),
    "ipc": ("level", "IPC interanual (%)"),
    "pib_indice": ("index", "PIB real (base 100 = investidura)"),
    "ipv_indice": ("index", "Precio vivienda IPV (base 100 = investidura)"),
    "coste_salarial": ("index", "Coste salarial nominal (base 100 = investidura)"),
}


def event_study(key: str, mode: str = "level", horizon_months: int = 48) -> pd.DataFrame:
    """Alinea la serie por meses desde la investidura de la XIV y la XV."""
    s = series(key).dropna()
    out = []
    for leg, start in (("XIV", XIV), ("XV", XV)):
        base = value_at(s, start)
        if not base:
            continue
        base_date, base_val = base
        window = s[(s.index >= base_date) & (s.index <= base_date + pd.DateOffset(months=horizon_months))]
        for fecha, val in window.items():
            months = (fecha.year - base_date.year) * 12 + fecha.month - base_date.month
            out.append({
                "legislatura": leg, "mes": months, "fecha": fecha,
                "valor": val / base_val * 100 if mode == "index" else val,
            })
    return pd.DataFrame(out)


# ─── Indicadores derivados ──────────────────────────────────────────────────
def quarterly_panel() -> pd.DataFrame:
    """Panel trimestral con los principales indicadores macro alineados."""
    ipc_q = to_quarterly(series("ipc"))
    ipc_idx_q = to_quarterly(series("ipc_indice"))
    panel = pd.concat({
        "paro": series("paro"),
        "paro_juvenil": series("paro_juvenil"),
        "pib": series("pib"),
        "ipc": ipc_q,
        "ipc_subyacente": to_quarterly(series("ipc_subyacente")),
        "ipc_indice": ipc_idx_q,
        "ipv": series("ipv"),
        "ipv_indice": series("ipv_indice"),
        "coste_salarial": series("coste_salarial"),
        "ocupados": series("ocupados"),
        "vacantes": series("vacantes"),
        "ipi": to_quarterly(series("ipi")),
        "tipo_hipoteca": to_quarterly(series("tipo_hipoteca")),
    }, axis=1).sort_index()
    panel["salario_yoy"] = panel["coste_salarial"].pct_change(4, fill_method=None) * 100
    panel["ocupados_yoy"] = panel["ocupados"].pct_change(4, fill_method=None) * 100
    panel["indice_miseria"] = panel["paro"] + panel["ipc"]
    panel["legislatura"] = [legislature_of(d) for d in panel.index]
    return panel


def legislature_of(fecha: pd.Timestamp) -> str:
    for leg in reversed(LEGISLATURES):
        if fecha >= pd.Timestamp(leg["start"]):
            return leg["id"]
    return "Anterior"


def real_wages(base: pd.Timestamp = XV) -> pd.DataFrame:
    """Salario nominal y real (deflactado con IPC), media móvil 4 trimestres."""
    wage = series("coste_salarial").rolling(4).mean()
    prices = to_quarterly(series("ipc_indice"))
    df = pd.concat({"nominal": wage, "ipc": prices}, axis=1).dropna()
    b = value_at(df["nominal"], base)[0]
    df["nominal_idx"] = df["nominal"] / df.loc[b, "nominal"] * 100
    df["ipc_idx"] = df["ipc"] / df.loc[b, "ipc"] * 100
    df["real_idx"] = df["nominal_idx"] / df["ipc_idx"] * 100
    df["nominal_yoy"] = df["nominal"].pct_change(4, fill_method=None) * 100
    df["ipc_yoy"] = df["ipc"].pct_change(4, fill_method=None) * 100
    df["real_yoy"] = df["nominal_yoy"] - df["ipc_yoy"]
    return df


def housing_affordability(base_year: int = 2015) -> pd.DataFrame:
    """Precio de la vivienda frente a salarios (ambos base 100 en ``base_year``)."""
    ipv = series("ipv_indice")
    wage = series("coste_salarial").rolling(4).mean()
    alquiler = series("alquiler_indice")
    df = pd.concat({"ipv": ipv, "salario": wage}, axis=1).dropna()
    ref = df[df.index.year == base_year].mean()
    df["ipv_idx"] = df["ipv"] / ref["ipv"] * 100
    df["salario_idx"] = df["salario"] / ref["salario"] * 100
    df["esfuerzo"] = df["ipv_idx"] / df["salario_idx"] * 100
    alq = alquiler[alquiler.index.year >= base_year]
    if not alq.empty:
        alq_idx = alq / alq.iloc[0] * 100
        df["alquiler_idx"] = alq_idx.reindex(df.index, method="ffill")
    return df


def sigma_convergence() -> pd.Series:
    """Dispersión (desviación típica) del paro entre CCAA, sin Ceuta y Melilla."""
    w = wide("paro_ccaa").drop(columns=["España", "Ceuta", "Melilla"], errors="ignore")
    return w.std(axis=1).dropna()


def correlation_matrix() -> pd.DataFrame:
    p = quarterly_panel()
    cols = ["paro", "pib", "ipc", "ipc_subyacente", "ipv", "salario_yoy", "ocupados_yoy", "tipo_hipoteca", "ipi"]
    return p[cols].dropna().corr().round(2)


def flows_12m() -> pd.DataFrame:
    """Flujos mensuales en suma móvil 12 meses (turismo, empresas, hipotecas, nacimientos)."""
    return pd.concat({
        "turistas": rolling_12m(series("turistas")),
        "gasto_turistas": rolling_12m(series("gasto_turistas")),
        "sociedades": rolling_12m(series("sociedades")),
        "hipotecas": rolling_12m(series("hipotecas")),
        "nacimientos": rolling_12m(series("nacimientos")),
    }, axis=1)


# ─── Territorio ─────────────────────────────────────────────────────────────
def _latest_and_start(key: str) -> pd.DataFrame:
    w = wide(key)
    if w.empty:
        return pd.DataFrame()
    latest = w.ffill().iloc[-1]
    start_rows = w[w.index <= XV]
    start = start_rows.ffill().iloc[-1] if not start_rows.empty else pd.Series(dtype=float)
    return pd.DataFrame({"latest": latest, "start": start})


def ccaa_table() -> pd.DataFrame:
    paro = _latest_and_start("paro_ccaa")
    out = pd.DataFrame({
        "paro": paro["latest"],
        "paro_delta": paro["latest"] - paro["start"],
        "empleo": _latest_and_start("empleo_ccaa")["latest"],
        "arope": _latest_and_start("arope_ccaa")["latest"],
        "ipv": _latest_and_start("ipv_ccaa")["latest"],
        "ipc": _latest_and_start("ipc_ccaa")["latest"],
        "salario": _latest_and_start("salario_ccaa")["latest"],
        "alquiler": _latest_and_start("alquiler_ccaa")["latest"],
    })
    gap = gender_gap_ccaa()
    out["brecha"] = gap
    return out.round(2)


# ─── Brecha de género ───────────────────────────────────────────────────────
def gap_pct(men: pd.Series, women: pd.Series) -> pd.Series:
    """Brecha salarial = (H − M) / H × 100. Positiva: los hombres ganan más."""
    df = pd.concat({"h": men, "m": women}, axis=1).dropna()
    return ((df["h"] - df["m"]) / df["h"] * 100).round(2)


def gender_gap() -> pd.DataFrame:
    return pd.concat({
        "anual_media": gap_pct(series("salario_hombres"), series("salario_mujeres")),
        "anual_mediana": gap_pct(series("salario_mediana_hombres"), series("salario_mediana_mujeres")),
        "por_hora": gap_pct(series("salario_hora_hombres"), series("salario_hora_mujeres")),
    }, axis=1)


def gender_gap_by(key_prefix: str) -> pd.DataFrame:
    """Brecha por dimensión (sector, ocupación, actividad) en el último año disponible."""
    h, m = wide(f"{key_prefix}_hombres"), wide(f"{key_prefix}_mujeres")
    year = min(h.dropna(how="all").index.max(), m.dropna(how="all").index.max())
    hh, mm = h.loc[year], m.loc[year]
    df = pd.DataFrame({"hombres": hh, "mujeres": mm}).dropna()
    df["brecha"] = (df["hombres"] - df["mujeres"]) / df["hombres"] * 100
    df.attrs["year"] = year.year
    return df.sort_values("brecha", ascending=False).round(2)


def gender_gap_ccaa() -> pd.Series:
    h, m = wide("salario_ccaa_hombres").ffill().iloc[-1], wide("salario_ccaa_mujeres").ffill().iloc[-1]
    return ((h - m) / h * 100).round(2)


def labour_gender() -> pd.DataFrame:
    return pd.concat({
        "paro_mujeres": series("paro_mujeres"),
        "paro_hombres": series("paro_hombres"),
        "brecha_paro_pp": series("paro_mujeres") - series("paro_hombres"),
        "empleo_mujeres": series("empleo_mujeres"),
        "empleo_hombres": series("empleo_hombres"),
    }, axis=1)


# ─── Justicia penal y nacionalidad ──────────────────────────────────────────
def _age_bounds(label: str) -> tuple[int, int] | None:
    label = label.lower()
    if m := re.match(r"de (\d+) a (\d+) años", label):
        return int(m.group(1)), int(m.group(2))
    if m := re.match(r"(\d+) y más años", label):
        return int(m.group(1)), 110
    return None


def _single_year(pop_by_group: pd.Series) -> pd.Series:
    """Reparte grupos quinquenales en edades simples (supuesto de distribución uniforme)."""
    values = np.zeros(111)
    for label, v in pop_by_group.items():
        b = _age_bounds(label)
        if b is None or pd.isna(v):
            continue
        lo, hi = b
        hi = min(hi, lo + 14) if hi == 110 else hi
        values[lo:hi + 1] += v / (hi - lo + 1)
    return pd.Series(values)


CONDENA_BANDS = ["De 18 a 20 años", "De 21 a 25 años", "De 26 a 30 años", "De 31 a 35 años", "De 36 a 40 años",
                 "De 41 a 50 años", "De 51 a 60 años", "De 61 a 70 años", "71 y más años"]


def population_by_nationality() -> pd.DataFrame:
    """Población media anual por nacionalidad (total / española / extranjera) y grupo de edad."""
    frames = []
    for nat, keys in {"total": ("pob_hist_total", "pob_total"), "española": ("pob_hist_espanola", "pob_espanola")}.items():
        w = pd.concat([wide(keys[0]), wide(keys[1])]).sort_index()
        w = w[~w.index.duplicated(keep="last")]
        annual = w.groupby(w.index.year).mean()
        annual["nacionalidad"] = nat
        frames.append(annual)
    tot, esp = frames
    ext = tot.drop(columns="nacionalidad") - esp.drop(columns="nacionalidad")
    ext["nacionalidad"] = "extranjera"
    df = pd.concat([tot, esp, ext])
    df.index.name = "anyo"
    return df


def population_in_bands(nat_df: pd.DataFrame) -> pd.DataFrame:
    """Convierte la población quinquenal a las franjas de edad de la estadística de condenados."""
    rows = []
    for (anyo, nat), r in nat_df.reset_index().set_index(["anyo", "nacionalidad"]).iterrows():
        single = _single_year(r.drop(labels=["Todas las edades"], errors="ignore"))
        rec = {"anyo": anyo, "nacionalidad": nat}
        for band in CONDENA_BANDS:
            lo, hi = _age_bounds(band)
            rec[band] = single[lo:min(hi, 110) + 1].sum()
        rec["18+"] = single[18:].sum()
        rows.append(rec)
    return pd.DataFrame(rows).set_index(["anyo", "nacionalidad"])


def convictions_by_age() -> pd.DataFrame:
    tot, esp = wide("condenados_edad_total"), wide("condenados_edad_espanola")
    tot.index, esp.index = tot.index.year, esp.index.year
    ext = tot - esp
    return pd.concat({"total": tot, "española": esp, "extranjera": ext}, names=["nacionalidad", "anyo"]) \
        .swaplevel().sort_index()


def _annual_mean(keys: tuple[str, str]) -> pd.DataFrame:
    w = pd.concat([wide(keys[0]), wide(keys[1])]).sort_index()
    w = w[~w.index.duplicated(keep="last")]
    return w.groupby(w.index.year).mean()


def population_sex_bands() -> pd.DataFrame:
    """Población media anual en franjas de condena, por nacionalidad y sexo."""
    sources = {"total": ("pob_hist_sexo_edad_total", "pob_sexo_edad_total"),
               "española": ("pob_hist_sexo_edad_espanola", "pob_sexo_edad_espanola")}
    rows = []
    for nat, keys in sources.items():
        annual = _annual_mean(keys)
        for anyo, r in annual.iterrows():
            for sexo in ("Hombres", "Mujeres"):
                groups = r[[c for c in r.index if c.endswith(f". {sexo}")]]
                groups.index = [c.rsplit(". ", 1)[0] for c in groups.index]
                single = _single_year(groups)
                rec = {"anyo": anyo, "nacionalidad": nat, "sexo": sexo}
                for band in CONDENA_BANDS:
                    lo, hi = _age_bounds(band)
                    rec[band] = single[lo:hi + 1].sum()
                rows.append(rec)
    df = pd.DataFrame(rows).set_index(["anyo", "nacionalidad", "sexo"])
    ext = df.xs("total", level=1) - df.xs("española", level=1)
    ext["nacionalidad"] = "extranjera"
    ext = ext.reset_index().set_index(["anyo", "nacionalidad", "sexo"])
    return pd.concat([df, ext]).sort_index()


def convictions_sex_bands() -> pd.DataFrame:
    frames = {}
    for nat, key in (("total", "condenados_sexo_edad_total"), ("española", "condenados_sexo_edad_espanola")):
        w = wide(key)
        w.index = w.index.year
        long = w.stack().rename("valor").reset_index()
        long[["sexo", "_nat", "band"]] = long["dim"].str.split(". ", n=2, expand=True, regex=False)
        frames[nat] = long.pivot_table(index=["fecha", "sexo"], columns="band", values="valor")
    tot, esp = frames["total"], frames["española"]
    ext = tot - esp
    out = pd.concat({"total": tot, "española": esp, "extranjera": ext}, names=["nacionalidad"])
    out.index.names = ["nacionalidad", "anyo", "sexo"]
    return out.reorder_levels(["anyo", "nacionalidad", "sexo"]).sort_index()[CONDENA_BANDS]


def conviction_rates() -> pd.DataFrame:
    """Tasas de condenados por 1.000 residentes de 18+ años: bruta, ajustada por edad y por edad y sexo.

    Estandarización directa: se aplica a cada nacionalidad la estructura por edad (y sexo)
    de la población adulta total del mismo año, de modo que la comparación no dependa de que
    la población extranjera sea, en promedio, más joven y más masculina.
    """
    pop = population_in_bands(population_by_nationality())
    conv = convictions_by_age()
    pop_s, conv_s = population_sex_bands(), convictions_sex_bands()
    years = sorted(set(conv.index.get_level_values(0)) & set(pop.index.get_level_values(0))
                   & set(conv_s.index.get_level_values(0)))
    rows = []
    for anyo in years:
        std = pop.loc[(anyo, "total"), CONDENA_BANDS]
        weights = std / std.sum()
        std_s = pop_s.loc[(anyo, "total")]
        weights_s = std_s / std_s.values.sum()
        for nat in ("total", "española", "extranjera"):
            c = conv.loc[(anyo, nat), CONDENA_BANDS]
            p = pop.loc[(anyo, nat), CONDENA_BANDS]
            specific = c / p * 1000
            specific_s = conv_s.loc[(anyo, nat)] / pop_s.loc[(anyo, nat)] * 1000
            sex_rates = (conv_s.loc[(anyo, nat)].sum(axis=1) / pop_s.loc[(anyo, nat)].sum(axis=1) * 1000)
            rows.append({
                "anyo": anyo, "nacionalidad": nat,
                "condenados": float(c.sum()),
                "poblacion_18": float(pop.loc[(anyo, nat), "18+"]),
                "tasa_bruta": float(c.sum() / pop.loc[(anyo, nat), "18+"] * 1000),
                "tasa_edad": float((specific * weights).sum()),
                "tasa_edad_sexo": float((specific_s * weights_s).values.sum()),
                "tasa_hombres": float(sex_rates["Hombres"]),
                "tasa_mujeres": float(sex_rates["Mujeres"]),
                **{f"tasa_{b}": float(v) for b, v in specific.items()},
            })
    df = pd.DataFrame(rows)
    piv = df.pivot(index="anyo", columns="nacionalidad", values=["tasa_bruta", "tasa_edad", "tasa_edad_sexo"])
    ratio = pd.DataFrame({
        f"ratio_{m}": piv[(f"tasa_{m}", "extranjera")] / piv[(f"tasa_{m}", "española")]
        for m in ("bruta", "edad", "edad_sexo")
    })
    return df.merge(ratio, left_on="anyo", right_index=True).round(3)


def age_structure() -> pd.DataFrame:
    """Distribución por edad de la población adulta española y extranjera (último año)."""
    pop = population_in_bands(population_by_nationality())
    year = pop.index.get_level_values(0).max()
    out = {}
    for nat in ("española", "extranjera"):
        p = pop.loc[(year, nat), CONDENA_BANDS]
        out[nat] = p / p.sum() * 100
    df = pd.DataFrame(out).round(2)
    df.attrs["year"] = int(year)
    return df


def conviction_sex_share() -> pd.DataFrame:
    h, m = wide("condenados_hombres_nac"), wide("condenados_mujeres_nac")
    share = (h / (h + m) * 100).round(2)
    share.index = share.index.year
    return share


def crimes_by_type(year: int | None = None, top: int = 14) -> pd.DataFrame:
    """Peso de condenas a extranjeros por tipo de delito frente a su peso en la población adulta."""
    tot, esp = wide("delitos_tipo_total"), wide("delitos_tipo_espanola")
    year_ts = tot.dropna(how="all").index.max() if year is None else pd.Timestamp(f"{year}-01-01")
    t, e = tot.loc[year_ts], esp.loc[year_ts]
    df = pd.DataFrame({"total": t, "española": e}).dropna()
    df["extranjera"] = df["total"] - df["española"]
    df = df[df["total"] >= 1000]
    df["pct_extranjera"] = df["extranjera"] / df["total"] * 100
    df = df.drop(index=[i for i in df.index if i.lower() == "delitos"], errors="ignore")
    df.attrs["year"] = year_ts.year
    return df.sort_values("total", ascending=False).head(top).round(2)


def foreign_adult_share() -> pd.Series:
    pop = population_in_bands(population_by_nationality())
    tot = pop.xs("total", level=1)["18+"]
    ext = pop.xs("extranjera", level=1)["18+"]
    return (ext / tot * 100).round(2)


# ─── Hallazgos automáticos ──────────────────────────────────────────────────
def _fmt(v: float, dec: int = 1) -> str:
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def insights() -> list[dict]:
    out: list[dict] = []

    def add(block: str, title: str, body: str, tone: str = "neutral") -> None:
        out.append({"block": block, "title": title, "body": body, "tone": tone})

    k = kpi("paro")
    paro = series("paro")
    since = paro.index[0].year
    title = (f"El paro, en mínimos de la serie (desde {since})" if k.latest <= paro.min() + 1e-9
             else f"El paro, cerca de sus mínimos desde {since}" if k.latest <= paro.min() + 0.5
             else "El paro baja en la legislatura" if k.delta < 0 else "El paro sube en la legislatura")
    add("empleo", title,
        f"La tasa de paro pasa de {_fmt(k.start, 2)}% ({period_label(k.start_date, 'Q')}) a {_fmt(k.latest, 2)}% "
        f"({period_label(k.latest_date, 'Q')}): {_fmt(k.delta, 2)} pp en la legislatura.", "good" if k.delta < 0 else "bad")

    k = kpi("ocupados")
    record = k.latest >= series("ocupados").max() * 0.995
    add("empleo", "Ocupación en máximos de la serie" if record else "Evolución de la ocupación",
        f"La EPA suma {_fmt(k.delta, 0)} mil ocupados desde el inicio de la XV, hasta {_fmt(k.latest / 1000, 2)} millones.",
        "good" if k.delta > 0 else "bad")

    k = kpi("paro_juvenil")
    ratio = k.latest / kpi("paro").latest
    add("empleo", f"Paro juvenil: {_fmt(ratio, 1)} veces la media",
        f"El paro de menores de 25 años está en {_fmt(k.latest)}% ({_fmt(k.delta)} pp desde el inicio de legislatura).",
        "good" if k.delta < 0 else "bad")

    k, ks, ke = kpi("ipc"), kpi("ipc_subyacente"), kpi("ipc_energia")
    driver = " La energía tira del índice general." if ke.latest > k.latest + 2 else ""
    add("precios", "La inflación repunta" if k.delta > 0 else "La inflación se modera",
        f"El IPC interanual pasa de {_fmt(k.start)}% a {_fmt(k.latest)}% ({period_label(k.latest_date, 'M')}); "
        f"la subyacente está en {_fmt(ks.latest)}% y la energía en {_fmt(ke.latest)}%.{driver}",
        "bad" if k.delta > 0 else "good")

    rw = real_wages()
    last = rw.iloc[-1]
    add("salarios", "Poder adquisitivo de los salarios",
        f"Desde el inicio de la legislatura el coste salarial nominal crece un {_fmt(last['nominal_idx'] - 100)}% y los precios un "
        f"{_fmt(last['ipc_idx'] - 100)}%: el salario real varía un {_fmt(last['real_idx'] - 100)}%.",
        "good" if last["real_idx"] > 100 else "bad")

    ha = housing_affordability()
    esfuerzo = ha["esfuerzo"].iloc[-1]
    add("vivienda", "La vivienda se aleja de los salarios" if esfuerzo > 100 else "La vivienda gana accesibilidad",
        f"Desde 2015 el precio de la vivienda (IPV) ha subido un {_fmt(ha['ipv_idx'].iloc[-1] - 100, 0)}% y los salarios un "
        f"{_fmt(ha['salario_idx'].iloc[-1] - 100, 0)}%. El índice de esfuerzo está en {_fmt(esfuerzo, 0)} (2015 = 100).",
        "bad" if esfuerzo > 100 else "good")

    k = kpi("pib")
    add("actividad", f"El PIB crece un {_fmt(k.latest, 1)}% interanual",
        f"Crecimiento real del PIB en {period_label(k.latest_date, 'Q')}, frente al {_fmt(k.start, 1)}% de "
        f"{period_label(k.start_date, 'Q')}.", "good" if k.latest > 1.5 else "neutral")

    k = kpi("arope")
    add("bienestar", "Pobreza y exclusión (AROPE)",
        f"La tasa AROPE se sitúa en {_fmt(k.latest)}% ({k.latest_date.year}), {_fmt(k.delta)} pp respecto a {k.start_date.year}: "
        f"afecta a aproximadamente 1 de cada {_fmt(100 / k.latest, 0)} residentes.", "good" if k.delta < 0 else "bad")

    g = gender_gap()
    gh = g["por_hora"].dropna()
    ga = g["anual_media"].dropna()
    add("genero", "La brecha salarial de género se estrecha",
        f"Por hora trabajada, las mujeres cobran un {_fmt(gh.iloc[-1])}% menos ({gh.index[-1].year}), frente al "
        f"{_fmt(gh.iloc[0])}% de {gh.index[0].year}. En ganancia anual la brecha es mayor ({_fmt(ga.iloc[-1])}%) "
        "por la mayor parcialidad femenina.", "good" if gh.iloc[-1] < gh.iloc[0] else "bad")

    cr = conviction_rates()
    last_y = cr["anyo"].max()
    r = cr[cr["anyo"] == last_y].set_index("nacionalidad")
    add("justicia", "Condenas por nacionalidad: la demografía explica parte de la diferencia",
        f"En {last_y} hay {_fmt(r.loc['extranjera', 'tasa_bruta'], 1)} condenados por mil adultos extranjeros y "
        f"{_fmt(r.loc['española', 'tasa_bruta'], 1)} por mil españoles (ratio {_fmt(r.loc['extranjera', 'ratio_bruta'], 2)}). "
        f"Al ajustar por edad y sexo el ratio baja a {_fmt(r.loc['extranjera', 'ratio_edad_sexo'], 2)}: la diferencia se reduce "
        "pero no desaparece. Son condenas, no delitos cometidos, e incluyen a no residentes.", "neutral")

    sc = sigma_convergence()
    add("territorio", "Convergencia territorial del paro",
        f"La desviación típica del paro entre CCAA cae de {_fmt(sc.iloc[0], 2)} pp ({period_label(sc.index[0], 'Q')}) a "
        f"{_fmt(sc.iloc[-1], 2)} pp: las regiones se parecen cada vez más.", "good" if sc.iloc[-1] < sc.iloc[0] else "bad")
    return out
