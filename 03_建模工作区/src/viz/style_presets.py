"""论文级绘图样式预设。

用法::

    from viz.style_presets import apply_style, save_figure

    apply_style("paper")           # 或 "screen"、"presentation"
    fig, ax = plt.subplots()
    ...
    save_figure(fig, "03_建模工作区/figures/fig1_error_curve", formats=("png", "pdf"))

设计原则（对标 SciencePlots 的 science/ieee 风格，不依赖 LaTeX）：
- 论文风格使用衬线字体、细线宽、紧凑留白，300 dpi 起；
- 项目图统一使用冷调紫蓝色板，并通过 marker/线型/纹理提供冗余编码；
- 所有 rc 参数集中在此文件，图模板不得散落硬编码样式。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# 项目唯一默认色板；语义与扩展规则见 VISUAL_STYLE_GUIDE.md。
PROJECT_COLORS: list[str] = [
    "#4F587D", "#776B97", "#C68DC0", "#C2E0EE", "#DBC4ED",
]

NEUTRAL_COLORS: dict[str, str] = {
    "ink": "#1B1F23",
    "dark": "#4E565E",
    "mid": "#8C949C",
    "light": "#C4CAD1",
    "paper": "#E8EEF4",
}


def project_sequential_cmap() -> LinearSegmentedColormap:
    """返回与项目色板一致的连续色图，不修改 matplotlib 全局注册表。"""
    return LinearSegmentedColormap.from_list(
        "project_purple_blue",
        ["#FFFFFF", "#C2E0EE", "#DBC4ED", "#C68DC0", "#776B97", "#4F587D"],
    )

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
    "axes.prop_cycle": plt.cycler(color=PROJECT_COLORS),
    "text.color": NEUTRAL_COLORS["ink"],
    "axes.labelcolor": NEUTRAL_COLORS["ink"],
    "xtick.color": NEUTRAL_COLORS["dark"],
    "ytick.color": NEUTRAL_COLORS["dark"],
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
        record = {
            "figure": str(stem),
            "formats": list(formats),
            "preset": mpl.rcParams.get("font.family", ""),
        }
        with mf.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return written
