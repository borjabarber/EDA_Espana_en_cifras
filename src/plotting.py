"""Estilo gráfico común para el notebook (paleta coherente con el dashboard)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from .catalog import LEGISLATURES

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "docs" / "img"

PALETTE = {
    "red": "#e63946",
    "gold": "#d4a72c",
    "green": "#2a9d8f",
    "blue": "#3d5a80",
    "sky": "#7aa2ff",
    "orange": "#f4845f",
    "ink": "#1d2433",
    "muted": "#7b8594",
    "grid": "#e8ebf0",
}
SERIES_COLORS = [PALETTE[c] for c in ("red", "blue", "gold", "green", "orange", "sky", "ink")]
LEG_COLORS = {"XII": "#f1f3f6", "XII-S": "#e9edf3", "XIV": "#f1f3f6", "XV": "#fdecee"}


def setup() -> None:
    plt.rcParams.update({
        "figure.figsize": (11, 4.6),
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#c9ced6",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": PALETTE["ink"],
        "axes.labelsize": 10,
        "axes.grid": True,
        "axes.prop_cycle": plt.cycler(color=SERIES_COLORS),
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.8,
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "legend.frameon": False,
        "legend.fontsize": 9,
        "font.family": "DejaVu Sans",
        "lines.linewidth": 2.0,
    })


def shade_legislatures(ax: plt.Axes, start: str | None = None, labels: bool = True) -> None:
    """Sombrea la XV Legislatura y marca el inicio de cada Gobierno."""
    xmin, xmax = ax.get_xlim()
    for leg in LEGISLATURES:
        s = pd.Timestamp(leg["start"])
        e = pd.Timestamp(leg["end"]) if leg["end"] else pd.Timestamp.today()
        if start and e < pd.Timestamp(start):
            continue
        if leg["id"] == "XV":
            ax.axvspan(s, e, color=LEG_COLORS["XV"], zorder=0, lw=0)
        ax.axvline(s, color=PALETTE["muted"], lw=0.8, ls=":", zorder=1)
        if labels:
            ax.text(s, 1.0, f" {leg['id']}", transform=ax.get_xaxis_transform(), fontsize=8,
                    color=PALETTE["red"] if leg["id"] == "XV" else PALETTE["muted"], va="top")
    ax.set_xlim(xmin, xmax)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def source(ax: plt.Axes, text: str) -> None:
    ax.annotate(f"Fuente: {text}", xy=(0, -0.16), xycoords="axes fraction", fontsize=8, color=PALETTE["muted"])


def save(fig: plt.Figure, name: str) -> Path:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = IMG_DIR / f"{name}.png"
    fig.savefig(path, facecolor="white")
    return path
