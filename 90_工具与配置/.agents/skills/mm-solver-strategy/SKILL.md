---
name: mm-solver-strategy
description: "AUTO TRIGGER: after G3 freeze of the MODEL_SPEC and before implementation, when the problem structure must be mapped to an ordered solver portfolio (closed form, LP, QP, convex, MILP, MINLP, CP-SAT, DP, shortest path/flow, TSP/VRP, local/global nonlinear, evolutionary, Bayesian/surrogate/simulation optimization) and tool availability probed. DO NOT TRIGGER: route comparison before G2, MODEL_SPEC drafting, actual coding (mm-implementation), tuning after G4, or validation. STAGE: S6b between G3 and S7. INPUTS: frozen MODEL_SPEC structure (variables, objective classes, constraint classes, scale). OUTPUTS: SOLVER_STRATEGY.md + portfolio decision record. BOUNDARIES: strategy only; never change the frozen model to fit a solver, never approve Gates."
---

# MM Solver Strategy

从冻结的 MODEL_SPEC 推导求解策略。产出 `03_建模工作区/model/SOLVER_STRATEGY.md`，
包含结构分类、求解器优先级、exact/relaxation 基线义务、报告义务。

## 流程

1. **结构识别**：从 MODEL_SPEC 提取目标与约束类别、变量连续性、规模（变量数/约束数/
   稀疏性/是否离散）。用 `python 90_工具与配置/scripts/solver_strategy.py --classify "<结构描述>"`
   起草，人工确认。
2. **探针**：`--probe` 检查本机可用求解器（cvxpy/ortools/pymoo/optuna/...），
   依赖缺失时在策略中写明降级链，不允许临场换模型。
3. **组合优先级**：每个问题类别给出有序 portfolio（exact 优先），明确：
   - 能建 exact 或 relaxation 基线的，**必须**先建 exact/松弛基线；
   - 启发式（evolutionary 等）只允许在 exact/local/global 全部不可行时启用，
     且必须报告 lower/upper bound、optimality gap、收敛曲线、≥5 seeds 方差、运行时间；
   - 大规模 LP/MILP 用 HiGHS（scipy 内置）；组合逻辑约束优先 CP-SAT。
4. **反模式自检**：不得因为 Agent 熟悉遗传算法就默认遗传算法；
   不得为迁就求解器改动冻结模型——若确需改动，走 MODEL_CHANGE_REQUEST。
5. **记录**：策略写入 SOLVER_STRATEGY.md 并登记 decisions；实现（mm-implementation）
   按此执行，reviewer 检查实现与策略一致。

## 决策表（摘要）

| 结构 | 首选 | 次选 | 基线义务 |
| --- | --- | --- | --- |
| 连续 LP | scipy linprog(HiGHS) | cvxpy / OR-Tools | 对偶界 |
| MILP | OR-Tools / scipy.milp | pyomo | MIP gap |
| 凸 | cvxpy（过 DCP 检查） | scipy | KKT/最优值 |
| 非凸局部 | scipy SLSQP/trust-constr 多起点 | — | best-of-N + localness 声明 |
| 全局 | differential_evolution/shgo | pymoo | 边界内验证 |
| 组合调度 | CP-SAT | DP | 可行解 + gap |
| 图上路径/流 | scipy.csgraph / networkx | OR-Tools | 精确 |
| TSP/VRP | OR-Tools routing + 2-opt | Held-Karp(n≤20) | LB 对比 |
| 黑箱昂贵 | Optuna(TPE) | GP-surrogate | 每 trial 记录 |
| 仿真优化 | 复制+公共随机数 | Optuna | 方差缩减声明 |

完整表见 `references/solver_portfolio.md` 与 `scripts/solver_strategy.py`。
