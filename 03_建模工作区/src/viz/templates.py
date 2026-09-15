"""竞赛常用图表模板库（全部基于 style_presets，禁止散落硬编码样式）。

每个函数返回 `(fig, axes)`，只画图不保存；保存统一用 `save_figure`。
所有模板接受真实数据数组；示例用法见各函数 docstring 与 `viz_smoke_test.py`。
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from viz.style_presets import OKABE_ITO


def line_comparison(
    x: Sequence[float],
    series: dict[str, Sequence[float]],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
) -> tuple[Figure, Axes]:
    """多方法对比折线图：模型对比、收敛曲线、误差曲线。

    series: {"方法名": y序列, ...}
    """
    fig, ax = plt.subplots()
    markers = itertools_cycle_markers()
    for (name, y), mk in zip(series.items(), markers):
        ax.plot(x, y, label=name, marker=mk, markersize=4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.legend()
    return fig, ax


def bar_with_error(
    categories: Sequence[str],
    values: Sequence[float],
    errors: Sequence[float] | None = None,
    ylabel: str = "",
    horizontal: bool = False,
) -> tuple[Figure, Axes]:
    """带误差棒的柱状图：多指标对比、灵敏度结果。"""
    fig, ax = plt.subplots()
    idx = np.arange(len(categories))
    if horizontal:
        ax.barh(idx, values, xerr=errors, color=OKABE_ITO[1], capsize=3)
        ax.set_yticks(idx, labels=categories)
        ax.invert_yaxis()
        if ylabel:
            ax.set_xlabel(ylabel)
    else:
        ax.bar(idx, values, yerr=errors, color=OKABE_ITO[1], capsize=3)
        ax.set_xticks(idx, labels=categories)
        if ylabel:
            ax.set_ylabel(ylabel)
    return fig, ax


def heatmap_annotated(
    matrix: np.ndarray,
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    cmap: str = "viridis",
    fmt: str = ".2f",
    colorbar_label: str = "",
) -> tuple[Figure, Axes]:
    """带数值标注的热力图：相关矩阵、混淆矩阵、灵敏度矩阵。"""
    matrix = np.asarray(matrix, dtype=float)
    fig, ax = plt.subplots()
    im = ax.imshow(matrix, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(col_labels)), labels=col_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)), labels=row_labels)
    thresh = (matrix.max() + matrix.min()) / 2 if matrix.size else 0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            color = "white" if matrix[i, j] < thresh else "black"
            ax.text(j, i, format(matrix[i, j], fmt), ha="center", va="center",
                    color=color, fontsize=7)
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    if colorbar_label:
        cb.set_label(colorbar_label)
    return fig, ax


def residual_diagnostic(
    fitted: Sequence[float],
    residuals: Sequence[float],
) -> tuple[Figure, tuple[Axes, Axes]]:
    """回归诊断双子图：残差-拟合值散点 + 残差 QQ 图。"""
    fitted = np.asarray(fitted, dtype=float)
    residuals = np.asarray(residuals, dtype=float)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.2))
    ax1.scatter(fitted, residuals, s=12, color=OKABE_ITO[5], alpha=0.7)
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xlabel("Fitted values")
    ax1.set_ylabel("Residuals")
    from scipy import stats
    stats.probplot(residuals, plot=ax2)
    ax2.set_xlabel("Theoretical quantiles")
    ax2.set_ylabel("Sample quantiles")
    fig.tight_layout()
    return fig, (ax1, ax2)


def sensitivity_tornado(
    param_names: Sequence[str],
    low_effects: Sequence[float],
    high_effects: Sequence[float],
    xlabel: str = "Output change",
) -> tuple[Figure, Axes]:
    """龙卷风图：单因素敏感性分析（围绕基线的低/高效应）。"""
    names = list(param_names)
    low = np.asarray(low_effects, dtype=float)
    high = np.asarray(high_effects, dtype=float)
    order = np.argsort(-np.abs(high - low))
    names = [names[i] for i in order]
    low, high = low[order], high[order]
    fig, ax = plt.subplots()
    idx = np.arange(len(names))
    ax.barh(idx, high - low, left=low, color=OKABE_ITO[6], alpha=0.85)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(idx, labels=names)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    return fig, ax


def pareto_front(
    costs: np.ndarray,
    labels: Sequence[str] | None = None,
    xlabel: str = "Objective 1",
    ylabel: str = "Objective 2",
) -> tuple[Figure, Axes]:
    """Pareto 前沿图：多目标优化结果（最小化两目标）。"""
    costs = np.asarray(costs, dtype=float)
    order = np.lexsort((costs[:, 1], costs[:, 0]))
    costs = costs[order]
    front_x, front_y = [], []
    best_y = np.inf
    for cx, cy in costs:
        if cy < best_y:
            front_x.append(cx)
            front_y.append(cy)
            best_y = cy
    fig, ax = plt.subplots()
    ax.scatter(costs[:, 0], costs[:, 1], s=18, color=OKABE_ITO[2], alpha=0.5,
               label="All solutions")
    fx, fy = np.asarray(front_x), np.asarray(front_y)
    ax.step(np.concatenate([[fx[0]], fx]), np.concatenate([fy, [fy[-1]]]),
            where="post", color=OKABE_ITO[3], linewidth=1.4, label="Pareto front")
    ax.scatter(fx, fy, s=26, color=OKABE_ITO[3], zorder=3)
    if labels:
        for (cx, cy), lb in zip(costs, labels):
            ax.annotate(lb, (cx, cy), fontsize=6, xytext=(3, 3),
                        textcoords="offset points")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    return fig, ax


def network_graph(
    edge_list: Iterable[tuple[int, int, float | None]],
    node_labels: Sequence[str] | None = None,
    layout_seed: int = 0,
    weight_label: str = "weight",
) -> tuple[Figure, Axes]:
    """加权网络图：图论/运筹题目的拓扑可视化（轻量，不依赖 networkx）。

    edge_list 元素为 (i, j, weight)；权重为 None 时按无权处理。
    """
    edges = list(edge_list)
    import networkx as nx  # 延迟导入：仅网络图需要
    g = nx.Graph()
    n = max(max(i, j) for i, j, *_ in edges) + 1
    g.add_nodes_from(range(n))
    for i, j, w in edges:
        g.add_edge(i, j, **({weight_label: w} if w is not None else {}))
    pos = nx.spring_layout(g, seed=layout_seed)
    fig, ax = plt.subplots()
    widths = [max(0.5, float(d.get(weight_label, 1.0))) for _, _, d in g.edges(data=True)]
    nx.draw_networkx_edges(g, pos, ax=ax, width=widths, alpha=0.5)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=180, node_color=OKABE_ITO[1])
    if node_labels:
        nx.draw_networkx_labels(g, pos, {i: lb for i, lb in enumerate(node_labels)},
                                font_size=7, ax=ax)
    ax.set_axis_off()
    return fig, ax


def _markers() -> list[str]:
    return ["o", "s", "^", "D", "v", "P", "X", "*"]


def itertools_cycle_markers() -> list[str]:
    """返回一组按系列循环的 marker（每个系列一个）。"""
    return _markers()
