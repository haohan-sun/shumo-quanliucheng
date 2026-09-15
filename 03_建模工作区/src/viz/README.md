# viz —— 竞赛可视化模板库

本文件仅为实现说明；唯一视觉规范源是 `90_工具与配置/configs/VISUAL_STYLE_GUIDE.md`。

可运行、色盲安全、论文级图表模板。7/7 模板通过冒烟测试（`tests/test_viz_templates.py`）。

## 快速开始

```python
import sys; sys.path.insert(0, "03_建模工作区/src")   # 或配置 PYTHONPATH
from viz.style_presets import apply_style, save_figure
from viz import templates
import matplotlib.pyplot as plt

apply_style("paper")                # paper / screen / presentation
fig, ax = templates.line_comparison(t, {"模型A": y1, "模型B": y2}, "时间 (h)", "误差")
save_figure(fig, "03_建模工作区/figures/fig3_error_comparison", formats=("png", "pdf"))
```

## 模板清单

| 模板 | 适用场景 |
| --- | --- |
| `line_comparison` | 多方法对比、收敛/误差曲线 |
| `bar_with_error` | 指标对比、带误差棒的分组柱状 |
| `heatmap_annotated` | 相关矩阵、混淆矩阵、灵敏度矩阵 |
| `residual_diagnostic` | 回归诊断（残差散点 + QQ 图） |
| `sensitivity_tornado` | 单因素灵敏度（龙卷风图） |
| `pareto_front` | 多目标优化 Pareto 前沿 |
| `network_graph` | 图论/网络拓扑（需 networkx，未装自动跳过） |

## 使用规则（与 CODE_STYLE.md 一致）

- 样式只经 `apply_style` 应用，绘图代码零散样式硬编码 = 违规。
- 正式图数据只能来自 `results/` 注册结果，导出走 `save_figure`（PNG 300dpi + 矢量）。
- G5 之前的**探索性作图**也用本库 + `apply_style("screen")`，输出到
  `experiments/scratch/`，不进 `figures/`、不写 manifest——正式图仍走
  mm-scientific-visualization 的 Figure Contract 流程。

## 外部风格参考

- [SciencePlots](https://github.com/garrettj403/SciencePlots)：`science`/`ieee`/`nature`
  风格基准（本库 `paper` 预设对标其无 LaTeX 版效果）。如需其原生样式：
  `uv pip install SciencePlots` 后 `plt.style.use(["science","no-latex"])`。
- `90_工具与配置/third_party/references/figures4papers/`：顶刊成品图参考集。
