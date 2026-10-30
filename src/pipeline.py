"""Descarga las tablas del INE definidas en el catálogo y genera datasets tidy.

Uso:
    python -m src.pipeline            # usa caché (< 24 h) si existe
    python -m src.pipeline --refresh  # fuerza la descarga

Salidas en ``data/processed``:
    series_long.csv  — formato largo: key, dim, fecha, anyo, periodo, valor
    catalog.csv      — metadatos y cobertura de cada serie
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from .catalog import CCAA, SERIES, SeriesSpec
from .ine_client import IneError, datos_tabla, table_url

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

NULT_BY_FREQ = {"M": 150, "Q": 52, "S": 60, "A": 16}
# El INE publica con signo negativo las celdas con muestra insuficiente en la EAES
NON_NEGATIVE_UNITS = {"€", "€/h", "personas", "delitos"}
CACHE_TTL_HOURS = 24


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def ccaa_name(raw: str) -> str | None:
    n = _norm(raw)
    for needle, canonical in CCAA:
        if needle in n:
            return canonical
    return None


def fetch_table(table_id: int, nult: int, refresh: bool = False) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / f"t{table_id}_n{nult}.json"
    if cache.exists() and not refresh:
        age_h = (time.time() - cache.stat().st_mtime) / 3600
        if age_h < CACHE_TTL_HOURS:
            return json.loads(cache.read_text(encoding="utf-8"))
    rows = datos_tabla(table_id, nult=nult)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def _points(serie: dict) -> list[dict]:
    out = []
    for d in serie.get("Data") or []:
        if d.get("Valor") is None or not d.get("Fecha"):
            continue
        fecha = datetime.fromisoformat(str(d["Fecha"]).replace("Z", "+00:00")).replace(tzinfo=None)
        out.append({
            "fecha": fecha.date().isoformat(),
            "anyo": d.get("Anyo"),
            "periodo": d.get("T3_Periodo"),
            "valor": float(d["Valor"]),
        })
    return out


def select(rows: list[dict], spec: SeriesSpec) -> dict[str, dict]:
    """Devuelve {dim: serie_ine}. En series simples la dim es ''."""
    picked: dict[str, dict] = {}
    rx = re.compile(spec.regex) if spec.regex else None
    for s in rows:
        name = s.get("Nombre") or ""
        n = _norm(name)
        if spec.exact is not None:
            if n != _norm(spec.exact):
                continue
            m = None
        else:
            m = rx.search(n) if rx else None
            if not m:
                continue
        if spec.multi is None:
            dim = ""
        else:
            raw_dim = m.group("dim") if m and "dim" in m.groupdict() else name
            if spec.multi == "ccaa":
                dim = ccaa_name(raw_dim)
                if dim is None:
                    continue
            else:
                # recuperar mayúsculas del nombre original
                start, end = m.span("dim")
                dim = re.sub(r"\s+", " ", name.strip())[start:end] if m else raw_dim
        current = picked.get(dim)
        if current is None or len(name) < len(current.get("Nombre") or ""):
            picked[dim] = s
    return picked


def build(refresh: bool = False, verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    nult_by_table: dict[int, int] = {}
    for spec in SERIES:
        nult_by_table[spec.table] = max(nult_by_table.get(spec.table, 0), NULT_BY_FREQ[spec.freq])

    tables: dict[int, list[dict]] = {}
    for tid, nult in nult_by_table.items():
        try:
            tables[tid] = fetch_table(tid, nult, refresh=refresh)
            log(f"  ✓ tabla {tid:>6}  {len(tables[tid]):>5} series")
        except IneError as exc:
            log(f"  ✗ tabla {tid:>6}  {exc}")
            tables[tid] = []

    records, catalog = [], []
    for spec in SERIES:
        picked = select(tables.get(spec.table, []), spec)
        n_obs, first, last = 0, None, None
        for dim, serie in picked.items():
            for p in _points(serie):
                if spec.unit in NON_NEGATIVE_UNITS and p["valor"] < 0:
                    continue
                records.append({"key": spec.key, "dim": dim, **p})
                n_obs += 1
                first = p["fecha"] if first is None or p["fecha"] < first else first
                last = p["fecha"] if last is None or p["fecha"] > last else last
        status = "ok" if picked else "sin coincidencias"
        log(f"  {'·' if picked else '!'} {spec.key:<18} {len(picked):>3} series  {n_obs:>5} obs  {first} → {last}")
        catalog.append({
            "key": spec.key,
            "block": spec.block,
            "label": spec.label,
            "unit": spec.unit,
            "freq": spec.freq,
            "better": spec.better,
            "source": spec.source,
            "table": spec.table,
            "table_url": table_url(spec.table),
            "n_series": len(picked),
            "n_obs": n_obs,
            "first": first,
            "last": last,
            "status": status,
            "nombre_ine": next(iter(picked.values()))["Nombre"].strip() if picked else None,
            "desc": spec.desc,
        })

    long_df = pd.DataFrame.from_records(records)
    long_df = long_df.drop_duplicates(["key", "dim", "fecha"]).sort_values(["key", "dim", "fecha"])
    catalog_df = pd.DataFrame.from_records(catalog)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(PROCESSED_DIR / "series_long.csv", index=False, encoding="utf-8")
    catalog_df.to_csv(PROCESSED_DIR / "catalog.csv", index=False, encoding="utf-8")
    log(f"\n{len(long_df):,} observaciones · {catalog_df['n_series'].sum()} series → {PROCESSED_DIR}")
    return long_df, catalog_df


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="ignora la caché y vuelve a descargar")
    args = parser.parse_args(argv)
    print("Descargando tablas del INE…")
    build(refresh=args.refresh)


if __name__ == "__main__":
    sys.exit(main())
