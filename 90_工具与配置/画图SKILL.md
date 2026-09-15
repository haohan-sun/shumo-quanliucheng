---
name: math-modeling-figure-legacy-reference
version: 0.1
language: zh-CN
license: CC-BY-4.0
summary: 面向数学建模竞赛论文的证据链式科研制图 Skill。先确定论文论点和数据证据，再选择图型、生成可复现图、做视觉与数值 QA；兼顾 CUMCM 风格、科研论文风格和答辩可读性。
status: LEGACY_REFERENCE_ONLY
authority: 视觉规则唯一来源为 `configs/VISUAL_STYLE_GUIDE.md`；本文件仅保留历史实现说明，不参与 Skill discovery。
legacy_triggers_not_active:
  - 数学建模论文配图
  - 数模作图
  - 路线图/路径图/轨迹图
  - 灵敏度分析/鲁棒性分析
  - Pareto/公平性/效率权衡
  - 算法流程图/模型框架图
  - 收敛图/消融图/对比图
  - 时空路径/甘特图/动态禁飞区
  - CUMCM/国赛/美赛/MCM/ICM 图表
---

# Math Modeling Figure Skill

## 0. 核心原则

数学建模论文中的图不是装饰，而是“模型—证据—结论”的视觉证书。任何正式图必须回答至少一个可陈述的问题：

- 输入数据是什么结构？
- 模型如何工作？
- 求解结果是什么？
- 为什么这个解可信？
- 与基线/其他方法相比改进在哪里？
- 参数变化后是否稳定？
- 约束何时起作用？

如果一张图不能支持论文中的一句明确结论，应优先删除或降级为附录。

## 1. 强制 Figure Contract

每张图开画前先写 7 项，不允许直接“看数据随便画”：

1. **Claim**：这张图要让评委相信什么？
2. **Evidence**：哪些真实数据字段直接支持该 Claim？
3. **Unit of observation**：一条路线 / 一个对象 / 一个 seed / 一个 Case / 一个时刻 / 一个参数点？
4. **Figure type**：为何该图型比表格或另一图型更适合？
5. **Panels**：是否需要 (a)(b)(c) 组成一条证据链？
6. **Provenance**：数据来自哪个 result/log/verifier/commit？
7. **Caption thesis**：图注第一句必须给出结论，而不是只说“结果如下”。

建议保存为 `figure_manifest.json`。

## 2. 数据真实性门禁

正式定量图只允许使用：

- 原始附件数据；
- 已冻结 result JSON/XLSX/CSV；
- verifier 重算数据；
- 从上述数据经可复现脚本派生的 tidy figure data。

禁止：

- 生成式图片模型编造点坐标、路径、误差棒、曲线；
- 为了“好看”移动数据点或调整数值；
- 用未验证 heuristic candidate 冒充 final；
- 将 UNKNOWN/TIMEOUT 绘制成 INFEASIBLE；
- 用插值曲线暗示不存在的连续数据；
- 用不同 y 轴缩放制造改进幅度。

AI 生成图像仅用于概念示意草稿；所有 quantitative figure 必须由真实数据脚本生成。

## 3. 数模论文图形体系

### 3.1 Overall / Framework Figure

用途：一页内讲清“问题 → 模型 → 算法 → 验证 → 输出”。

适合：
- 总体算法框架；
- 多问题继承关系；
- 多生成器→验证→最终选择；
- 静态规划→动态修复。

优先工具：TikZ / Graphviz / SVG。

规则：
- 4–8 个核心模块；
- 箭头表示真实数据流，不表示模糊“相关”；
- 算法名和数学目标分层；
- 不堆 20 个彩色框；
- 一种颜色对应一种语义层。

### 3.2 Input / Geometry Figure

用途：让评委立刻理解数据空间与约束。

适合：
- 点位地图；
- 等级/类别空间分布；
- 聚类区域；
- 障碍/NFZ；
- 网络/邻接结构。

规则：
- 坐标有物理意义时 `axis('equal')`；
- 比例尺/单位明确；
- marker 形状与颜色双编码关键类别；
- 基地/关键边界必须显式标识；
- 点太密时用透明度、hexbin 或 density，不用巨大 marker。

### 3.3 Route / Trajectory Figure

用途：展示调度、路径和任务分配。

推荐层级：
1. 任务点背景；
2. 决策对象路径；
3. 方向/访问次序；
4. 关键约束/障碍；
5. 只标关键事件，不给每条边都加箭头。

高级表达：
- **Route Cloud**：候选路线低 alpha 叠加 + final route 高亮；
- **Before/After**：静态路线 vs 动态修复；
- **Small Multiples**：同一尺度下不同 Case/时刻并排；
- **Migration**：P1→P2/P3 任务跨资源或对象转移矩阵/Sankey。

禁止：
- 20 条路线全部高饱和实线；
- 每个点都写编号导致不可读；
- 坐标轴比例失真；
- 把真实 detour 画成直线。

### 3.4 Optimization / Trade-off Figure

适合：
- Pareto frontier；
- epsilon constraint；
- makespan vs fairness；
- 参数—目标关系；
- N vs Tmax；
- LB/UB gap。

推荐：
- scatter + connected frontier；
- dumbbell/slopegraph；
- confidence band；
- evidence-status strip。

若只有 5 个 epsilon 点，优先真实离散点，不拟合平滑曲线。

### 3.5 Workload / Fairness Figure

适合：
- 资源或执行主体的作业时长；
- Tmin/Tmax/Delta；
- P1→P2 前后变化。

优先：
- dumbbell；
- ordered dot plot；
- ECDF/box/violin（有足够样本时）；
- paired slopegraph。

执行主体较少时，不用箱线图掩盖个体数据。

### 3.6 Temporal / Scheduling Figure

适合：
- 甘特图；
- service / flight / wait / detour；
- 动态禁飞时段；
- Safe Interval；
- earliest-arrival envelope。

规则：
- 时间轴统一；
- 活动类型固定语义编码；
- NFZ active window 用背景带；
- 5 min service 显式区分飞行/等待；
- `[start,end)` 等边界语义可直接写入图注。

### 3.7 Validation / Robustness Figure

适合：
- multi-seed 稳定性；
- sensitivity；
- ablation；
- verifier before/after；
- residual/error；
- convergence。

原则：
- 先展示 raw points，再考虑均值/误差棒；
- n 小时不要装作统计推断；
- error bar 必须写清 SD/SE/CI；
- convergence 图必须区分 incumbent 与 current state；
- ablation 只画真正做过的模块。

### 3.8 Proof / Status Figure

数学建模中“证明状态”是特殊图类。

允许状态：
- PROVEN_INFEASIBLE
- FEASIBLE_WITNESS
- OPTIMAL
- UNKNOWN
- TIMEOUT
- RELAXATION_BOUND
- HEURISTIC_BEST

这些状态必须视觉上分离。尤其 UNKNOWN/TIMEOUT 不能使用与 infeasible 相同的叉号或红色语义。

## 4. 图型选择矩阵

| 论文问题 | 首选图 | 次选 | 不推荐 |
|---|---|---|---|
| 空间点位/任务分布 | scatter/map | density/hexbin | 3D scatter 无意义抬维 |
| 多主体路线 | equal-axis route map | small multiples | chord diagram 代替真实路线 |
| 候选解结构多样性 | Route Cloud | similarity heatmap | 只列 route 表格 |
| 负载均衡 | dumbbell | dot/slope | 只有 4 个主体时箱线图 |
| 效率公平权衡 | Pareto scatter | epsilon line | 双 Y 轴 |
| 参数敏感性 | line + raw points | heatmap | 3D surface（除非双参数连续响应） |
| 多参数双维响应 | contour/heatmap | 3D surface 辅助 | 只给 3D 不给投影 |
| 时序活动 | Gantt | timeline | 饼图 |
| 动态障碍 | time-slice maps | animation/interactive | 一张静态图塞全时间 |
| 算法机制 | TikZ/Graphviz | SVG schematic | 生成式“科技风”图 |
| 证明状态 | status strip / LB-UB | table | 把 timeout 画成失败 |
| 算法性能 | paired dots / bars + raw | table | 雷达图做精确比较 |

## 5. 高奖论文导向的版式策略

本 Skill 参考 CUMCM 官方公开展示论文的共同写作语境，同时吸收科研期刊制图规范。默认追求“评委 10 秒读懂 + 数据可复核”，而不是追求复杂视觉特效。

### 正文 Figure 分级

**A 级：必须正文**
- 问题/输入结构图；
- 关键模型机制图；
- 主要结果图；
- 最关键的验证/权衡图。

**B 级：正文视篇幅**
- 参数敏感性；
- 算法对比；
- 中间结构解释；
- 个别 Case 细节。

**C 级：附录**
- 所有 seed；
- 全参数 sweep；
- 完整路线编号；
- 大型诊断图；
- 重复性证明。

### 一张复合图应形成证据链

例如路径规划问题优先：

(a) 输入空间与约束 →
(b) 候选/模型机制 →
(c) 最终路径 →
(d) 关键指标/验证

而不是把四个无关 chart 拼在一起。

## 6. 颜色与视觉编码

默认：
- 白背景；
- 低饱和、色盲友好；
- 关键结果用高对比强调；
- 相同语义全篇固定颜色；
- 同一 Case/算法跨图保持一致编码。

颜色不能是唯一编码：关键类别同时用 marker/line style/annotation 区分。

避免：
- jet/rainbow；
- 荧光高饱和；
- 3D 柱状图；
- 阴影/渐变装饰；
- 饼图（除非纯构成且类别极少）；
- 雷达图进行精确数值比较；
- 双 Y 轴，除非确有同一因果时间轴且无法替代，并在图注解释。

## 7. 3D 使用门槛

3D 不是“高级”的默认表达。只有当第三维本身是模型变量且二维投影会丢失关键结构时才使用。

允许：
- 双连续参数目标曲面；
- 真实三维空间轨迹；
- 地形/物理场。

若用 3D，必须同时提供二维 contour/projection 之一，避免透视遮挡误导。

## 8. 数学建模专用 Figure Patterns

### Pattern A — Route Cloud

数据：`route_id, generator, entity_id, x1,y1,x2,y2, selected, verified`。

面板：B1 / B2 / B3 / final。

绘制：候选 route `alpha≈0.05–0.15`，final 加粗；可附 edge-density raster。

Claim 示例：多生成器产生互补拓扑，最终解从验证过的 route pool 中选择/重组。

### Pattern B — Giant Tour → Split

面板：
1. giant-tour 序列；
2. threshold feasibility；
3. cut positions；
4. K 条 route cost。

若实际实现是阈值二分 + 贪心精确分段，不得画成 DP 表。

### Pattern C — Epsilon Fairness Frontier

x: efficiency loss / epsilon 或 Tmax；
y: Delta / fairness metric。

展示所有真实 epsilon 点，推荐点加 outline，图注说明 selection rule。

### Pattern D — Earliest Arrival Envelope

x: departure time；
y: earliest feasible arrival。

绘制 direct / wait / detour candidate 及其 lower envelope，背景标目标 safe intervals。

### Pattern E — Time-slice Map

同坐标范围下展示 t1/t2/t3/t4：
- active NFZ；
- entity position；
- executed route；
- remaining route；
- waiting state。

### Pattern F — Nmin Evidence Strip

横轴 N；每格展示 proof status + best Tmax/LB。

UNKNOWN 与 PROVEN_INFEASIBLE 必须不同 glyph。

## 9. 实现技术栈优先级

### 定量图
1. Python + Matplotlib OO API
2. NumPy/Pandas 数据变换
3. NetworkX（网络/图结构）
4. Plotly（仅答辩交互或需要 hover 时）

### 机制图
1. TikZ
2. Graphviz
3. 手工 SVG

### 后期
- SVG/PDF 保持矢量；
- 必要时 Illustrator/Inkscape 仅做排版，不修改数据几何；
- 所有后期动作必须可记录。

### 禁止
- Excel 截图作为正式图；
- 屏幕截图 matplotlib window；
- AI image generator 生成定量曲线/坐标图。

## 10. 输出规格

每张正式图至少生成：

```
figures/
  figXX_name.svg
  figXX_name.pdf
  figXX_name.png
  figXX_name_source.csv
  figXX_name.py
```

推荐 PNG：300–600 dpi。

输出前检查实际论文尺寸：
- 单栏约 80–90 mm；
- 双栏/通栏按模板宽度；
- 缩放后正文仍能读刻度、legend、panel label。

不要依赖“放大 PDF 才看得清”。

## 11. Caption Protocol

每个图注按三句组织：

1. **结论句**：这张图说明什么；
2. **编码句**：颜色/线型/点/阴影表示什么；
3. **数据句**：数据来源、Case/seed/config、误差定义或 verifier 状态。

避免：
“图 5 为算法结果图。”

推荐：
“图 5 表明 ε=0.005 已将负载极差显著压缩，而 Tmax 仅小幅增加；实心点为经统一 verifier 复算的可行解，连线仅用于引导阅读。”

## 12. QA Checklist（强制）

### Data QA
- [ ] 所有点/线都能追溯到 source data
- [ ] 单位正确
- [ ] 分类顺序正确
- [ ] 没有 stale result
- [ ] final 与 verifier 一致
- [ ] UNKNOWN/TIMEOUT 未被误画

### Visual QA
- [ ] 实际论文尺寸可读
- [ ] 无文字裁切
- [ ] legend 不遮数据
- [ ] panel 对齐
- [ ] 坐标范围合理
- [ ] 空间图 equal aspect
- [ ] 颜色不是唯一编码
- [ ] 灰度下仍能辨识核心信息

### Modeling QA
- [ ] 图与正文 objective/constraint 一致
- [ ] 未画代码里不存在的算法模块
- [ ] 未将启发式结果描述成 proof
- [ ] 未把 restricted-pool optimality 写成 global optimality
- [ ] 未把局部 path-search failure 写成 physical infeasible

### Export QA
- [ ] SVG/PDF 矢量文本正常
- [ ] PNG 300+ dpi
- [ ] 字体嵌入/替换无异常
- [ ] figure data 与脚本一同保存

## 13. 执行顺序

收到一个数学建模作图任务时，严格执行：

1. 读题/论文上下文；
2. 找到该图支持的 Claim；
3. 定位冻结数据与 verifier；
4. 写 Figure Contract；
5. 选择图型；
6. 生成 tidy figure data；
7. 用 Matplotlib/TikZ/Graphviz 制图；
8. 导出 SVG/PDF/PNG；
9. 数值 QA；
10. 视觉 QA；
11. 论文尺寸 QA；
12. 写 caption；
13. 写 provenance manifest。

若第 3 步没有可靠数据，停止正式定量作图，只允许出 template/mockup，并显式标记 `PLACEHOLDER`。

## 14. 竞赛时间紧时的最小高质量策略

如果时间不足，不追求“每个模型一张花哨图”。按以下优先级：

1. 一张总体框架图；
2. 一张输入/几何图；
3. 每问一张最核心结果图；
4. 一张验证/敏感性/公平权衡图；
5. 其余进入附录。

少而强的证据链优于大量重复图。
