"""Regenera todo el proyecto de principio a fin.

    python run_all.py              # usa la caché de descargas (< 24 h)
    python run_all.py --refresh    # fuerza la descarga de todas las tablas del INE
    python run_all.py --skip-notebook

Pasos: descarga y limpieza (src.pipeline) → dashboard (src.build_dashboard)
→ generación y ejecución del notebook del EDA (que también regenera docs/img).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "notebooks" / "eda_xv_legislatura.ipynb"


def step(title: str, cmd: list[str]) -> None:
    print(f"\n▶ {title}\n  $ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"  ✓ {time.time() - t0:.0f} s", flush=True)


def main() -> None:
    args = set(sys.argv[1:])
    py = sys.executable
    step("1/4 Descarga y limpieza de series INE", [py, "-m", "src.pipeline", *(["--refresh"] if "--refresh" in args else [])])
    step("2/4 Dashboard HTML", [py, "-m", "src.build_dashboard"])
    if "--skip-notebook" not in args:
        step("3/4 Generación del notebook", [py, "scripts/build_notebook.py"])
        step("4/4 Ejecución del notebook y figuras", [py, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                                                     "--inplace", "--ExecutePreprocessor.timeout=900", str(NOTEBOOK)])
    print("\nListo. Abre dashboard/index.html en el navegador.")


if __name__ == "__main__":
    main()
