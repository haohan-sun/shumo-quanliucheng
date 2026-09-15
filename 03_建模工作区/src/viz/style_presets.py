"""论文级绘图样式预设。

用法::

    from viz.style_presets import apply_style, save_figure

    apply_style("paper")           # 或 "screen"、"presentation"
    fig, ax = plt.subplots()
    ...
    save_figure(fig, "03_建模工作区/figures/fig1_error_curve", formats=("png", "pdf"))

设计原则（对标 SciencePlots 的 science/ieee 风格，不依赖 LaTeX）：
- 论文风格使用衬线字体、细线宽、紧凑留白，300 dpi 起；
- 配色一律色盲安全（基于 Okabe-Ito / Paul Tol 色板）；
- 所有 rc 参数集中在此文件，图模板不得散落硬编码样式。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt

# Okabe-Ito 色盲安全色板
OKABE_ITO: list[str] = [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]

# 高对比顺序色板（热图等，ColorBrewer "viridis" 之外的手工替代）
SEQUENTIAL_CMAP_CANDIDATES = ["viridis", "cividis"]  # cividis 为色盲优化

_COMMON = {
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "legend.frameon": False,
    "axes.prop_cycle": plt.cycler(color=OKABE_ITO[1:]),
}

_PRESETS = {
    # 黑白打印友好的论文风格：衬线、细线、单栏宽度
    "paper": {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "lines.linewidth": 1.4,
        "lines.markersize": 4,
        "figure.figsize": (5.0, 3.2),   # 单栏 ~12.7cm
        "axes.linewidth": 0.8,
    },
    # 屏幕查看 / 评审预览：无衬线、稍大字号
    "screen": {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "font.size": 11,
        "axes.labelsize": 11,
        "figure.figsize": (7.0, 4.5),
        "lines.linewidth": 1.8,
    },
    # 答辩幻灯片：大字号、粗线
    "presentation": {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "font.size": 14,
        "axes.labelsize": 15,
        "axes.titlesize": 16,
        "legend.fontsize": 13,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "lines.linewidth": 2.4,
        "lines.markersize": 7,
        "figure.figsize": (8.0, 5.0),
    },
}


def apply_style(preset: str = "paper") -> None:
    """应用命名样式预设（paper / screen / presentation）。"""
    if preset not in _PRESETS:
        raise ValueError(f"未知样式预设 {preset!r}，可选：{sorted(_PRESETS)}")
    mpl.rcParams.update(_COMMON)
    mpl.rcParams.update(_PRESETS[preset])


def save_figure(
    fig: plt.Figure,
    stem: str | Path,
    formats: Sequence[str] = ("png", "pdf"),
    manifest: str | Path | None = None,
) -> list[Path]:
    """把图保存为多种格式；若给 manifest 路径则追加一条图记录（供 Figure Contract 使用）。

    stem 是不含扩展名的输出路径；manifest 为 JSON Lines 文件。
    """
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        out = stem.with_suffix(f".{fmt}")
        fig.savefig(out)
        written.append(out)
    if manifest is not None:
        mf = Path(manifest)
        mf.parent.mkdir(parents=True, exist_ok=True)
        record = {"figure": str(stem), "formats": list(formats), "preset": mpl.rcParams.get("font.family", "")}
        with mf.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return written
