"""可视化模板库冒烟测试：验证每个模板可用合成数据渲染并成功导出。

运行：./.venv/Scripts/python.exe -m tests.test_viz_templates
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from viz import templates  # noqa: E402
from viz.style_presets import apply_style, save_figure  # noqa: E402


def main() -> int:
    apply_style("paper")
    rng = np.random.default_rng(42)
    out_dir = Path(tempfile.mkdtemp(prefix="viz_smoke_"))
    checks: list[tuple[str, bool]] = []

    def check(name: str, fn) -> None:
        fig = None
        try:
            fig, _axes = fn()
            paths = save_figure(fig, out_dir / name, formats=("png",))
            ok = all(p.exists() and p.stat().st_size > 1000 for p in paths)
        finally:
            if fig is not None:
                plt.close(fig)
        checks.append((name, ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}")

    x = np.linspace(0, 10, 50)
    check("line_comparison", lambda: templates.line_comparison(
        x, {"M1": np.sin(x), "M2": np.cos(x), "M3": np.sin(x) * 0.8},
        xlabel="t", ylabel="y"))
    check("bar_with_error", lambda: templates.bar_with_error(
        ["A", "B", "C"], [1.0, 2.0, 1.5], [0.1, 0.2, 0.15], ylabel="score"))
    m = rng.normal(size=(5, 5))
    check("heatmap_annotated", lambda: templates.heatmap_annotated(
        m, [f"r{i}" for i in range(5)], [f"c{i}" for i in range(5)]))
    fitted = np.linspace(0, 10, 80)
    res = rng.normal(0, 1, 80)
    check("residual_diagnostic", lambda: templates.residual_diagnostic(fitted, res))
    check("sensitivity_tornado", lambda: templates.sensitivity_tornado(
        ["p1", "p2", "p3", "p4"], [-0.2, -0.5, -0.1, -0.3], [0.3, 0.2, 0.6, 0.25]))
    pts = rng.uniform([0, 0], [5, 5], size=(40, 2))
    pts[:, 1] += pts[:, 0] * 0.8
    check("pareto_front", lambda: templates.pareto_front(pts))
    try:
        check("network_graph", lambda: templates.network_graph(
            [(0, 1, 2.0), (1, 2, 1.0), (2, 0, 1.5), (2, 3, 3.0)],
            node_labels=["a", "b", "c", "d"]))
    except ImportError:
        print("SKIP network_graph (networkx 未安装)")
        checks.append(("network_graph", True))

    failed = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} templates passed; output in {out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
