"""Cliente mínimo para la API JSON Tempus3 del INE.

Documentación oficial: https://www.ine.es/dyngs/DataLab/manual.html?cid=45
No requiere autenticación. Algunas tablas grandes responden con
{"status": "Petición en proceso..."} mientras el INE las prepara; en ese caso
se reintenta con espera creciente.
"""
from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://servicios.ine.es/wstempus/js/ES"


class IneError(RuntimeError):
    """Error al consultar la API del INE."""


def fetch_json(path: str, params: dict | None = None, retries: int = 6, backoff: float = 3.0) -> Any:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    last: Any = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params or {}, timeout=180)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            last = str(exc)
        else:
            if isinstance(data, dict) and "status" in data:
                last = data["status"]
            else:
                return data
        time.sleep(backoff * (attempt + 1))
    raise IneError(f"{url} {params or ''} -> {last}")


def datos_tabla(table_id: int, nult: int | None = None) -> list[dict]:
    """Devuelve todas las series de una tabla Tempus3 (formato amigable `tip=A`)."""
    params: dict[str, Any] = {"tip": "A"}
    if nult:
        params["nult"] = nult
    data = fetch_json(f"DATOS_TABLA/{table_id}", params)
    if not isinstance(data, list):
        raise IneError(f"Respuesta inesperada para la tabla {table_id}: {type(data).__name__}")
    return data


def table_url(table_id: int) -> str:
    """URL pública de la tabla en INEbase."""
    return f"https://www.ine.es/jaxiT3/Tabla.htm?t={table_id}"
