"""Tiny dependency-free SVG renderer for the toy demo figure.

Shared by the baseline script and the standalone re-render script so both emit
byte-identical output for identical input.  Only the standard library is used,
so the demo renders even in a minimal environment.
"""

from __future__ import annotations

import csv
from pathlib import Path

WIDTH = 720
HEIGHT = 420
MARGIN_LEFT = 70
MARGIN_RIGHT = 30
MARGIN_TOP = 44
MARGIN_BOTTOM = 60

# Cool blue-violet family: each colour carries exactly one meaning, and the two
# series also differ by shape so the figure survives greyscale printing.
COLOR_OBSERVED = "#2f3b73"
COLOR_FITTED = "#8a63d2"
COLOR_AXIS = "#3b3f52"
COLOR_GRID = "#dfe1ee"


def read_predictions(path: Path) -> list[tuple[float, float, float]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [(float(row["t"]), float(row["y"]), float(row["y_hat"])) for row in reader]


def write_svg(
    rows: list[tuple[float, float, float]],
    output: Path,
    *,
    title: str,
    subtitle: str,
) -> None:
    xs = [row[0] for row in rows]
    ys = [value for row in rows for value in (row[1], row[2])]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    pad = (y_max - y_min) * 0.08 or 0.1
    y_min -= pad
    y_max += pad
    plot_w = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    plot_h = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    font = "Segoe UI, Arial, sans-serif"

    def px(x: float) -> float:
        return MARGIN_LEFT + (x - x_min) / (x_max - x_min) * plot_w

    def py(y: float) -> float:
        return MARGIN_TOP + plot_h - (y - y_min) / (y_max - y_min) * plot_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{title}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<text x="{MARGIN_LEFT}" y="22" font-family="{font}" font-size="15" '
        f'fill="{COLOR_AXIS}">{title}</text>',
        f'<text x="{MARGIN_LEFT}" y="38" font-family="{font}" font-size="11" '
        f'fill="{COLOR_AXIS}">{subtitle}</text>',
    ]

    for index in range(6):
        y_value = y_min + (y_max - y_min) * index / 5
        y_pixel = py(y_value)
        parts.append(
            f'<line x1="{MARGIN_LEFT}" y1="{y_pixel:.2f}" x2="{MARGIN_LEFT + plot_w}" '
            f'y2="{y_pixel:.2f}" stroke="{COLOR_GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{MARGIN_LEFT - 10}" y="{y_pixel + 4:.2f}" text-anchor="end" '
            f'font-family="{font}" font-size="10" fill="{COLOR_AXIS}">{y_value:.2f}</text>'
        )
    for index in range(6):
        x_value = x_min + (x_max - x_min) * index / 5
        parts.append(
            f'<text x="{px(x_value):.2f}" y="{MARGIN_TOP + plot_h + 18}" text-anchor="middle" '
            f'font-family="{font}" font-size="10" fill="{COLOR_AXIS}">{x_value:.0f}</text>'
        )

    parts.append(
        f'<line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP}" x2="{MARGIN_LEFT}" '
        f'y2="{MARGIN_TOP + plot_h}" stroke="{COLOR_AXIS}" stroke-width="1.2"/>'
    )
    parts.append(
        f'<line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP + plot_h}" x2="{MARGIN_LEFT + plot_w}" '
        f'y2="{MARGIN_TOP + plot_h}" stroke="{COLOR_AXIS}" stroke-width="1.2"/>'
    )

    curve = " ".join(f"{px(row[0]):.2f},{py(row[2]):.2f}" for row in rows)
    parts.append(
        f'<polyline points="{curve}" fill="none" stroke="{COLOR_FITTED}" stroke-width="2.2"/>'
    )
    for t, y, _ in rows:
        parts.append(
            f'<circle cx="{px(t):.2f}" cy="{py(y):.2f}" r="3.1" fill="{COLOR_OBSERVED}" '
            f'fill-opacity="0.85" stroke="#ffffff" stroke-width="0.8"/>'
        )

    legend_y = MARGIN_TOP - 12
    parts.extend(
        [
            f'<circle cx="{MARGIN_LEFT + plot_w - 132}" cy="{legend_y}" r="3.1" '
            f'fill="{COLOR_OBSERVED}"/>',
            f'<text x="{MARGIN_LEFT + plot_w - 122}" y="{legend_y + 4}" font-family="{font}" '
            f'font-size="11" fill="{COLOR_AXIS}">measured</text>',
            f'<line x1="{MARGIN_LEFT + plot_w - 62}" y1="{legend_y}" '
            f'x2="{MARGIN_LEFT + plot_w - 42}" y2="{legend_y}" stroke="{COLOR_FITTED}" '
            f'stroke-width="2.2"/>',
            f'<text x="{MARGIN_LEFT + plot_w - 36}" y="{legend_y + 4}" font-family="{font}" '
            f'font-size="11" fill="{COLOR_AXIS}">fitted</text>',
            f'<text x="{MARGIN_LEFT + plot_w / 2:.0f}" y="{HEIGHT - 18}" text-anchor="middle" '
            f'font-family="{font}" font-size="12" fill="{COLOR_AXIS}">time t (s)</text>',
            f'<text x="18" y="{MARGIN_TOP + plot_h / 2:.0f}" text-anchor="middle" '
            f'transform="rotate(-90 18 {MARGIN_TOP + plot_h / 2:.0f})" font-family="{font}" '
            f'font-size="12" fill="{COLOR_AXIS}">response y (V)</text>',
        ]
    )
    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_png_if_available(
    rows: list[tuple[float, float, float]], output: Path, *, title: str, subtitle: str
) -> bool:
    """Optional raster preview; returns False when matplotlib is unavailable."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure
    except Exception:
        return False
    figure = Figure(figsize=(7.2, 4.2), dpi=100)
    axes = figure.add_subplot(111)
    axes.plot(
        [row[0] for row in rows],
        [row[2] for row in rows],
        color=COLOR_FITTED,
        linewidth=2.2,
        label="fitted",
    )
    axes.scatter(
        [row[0] for row in rows],
        [row[1] for row in rows],
        s=14,
        color=COLOR_OBSERVED,
        edgecolor="white",
        linewidth=0.6,
        label="measured",
        zorder=3,
    )
    axes.set_xlabel("time t (s)")
    axes.set_ylabel("response y (V)")
    axes.set_title(f"{title}\n{subtitle}", fontsize=10)
    axes.grid(color=COLOR_GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(COLOR_AXIS)
    axes.legend(frameon=False, fontsize=9)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, format="png")
    return True
