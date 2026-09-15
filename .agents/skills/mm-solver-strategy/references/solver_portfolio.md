# Solver Portfolio 完整决策表

与 `90_工具与配置/scripts/solver_strategy.py::PORTFOLIO` 保持同步（该脚本为准）。
每个条目：family（exact/local/global/heuristic/surrogate/simulation）、工具、
必须报告的量、典型失败模式、降级链。

## exact 家族（默认首选）

- **closed_form**：sympy 求驻点/解析解。报告：解的存在性与唯一性论证。
  失败：无闭式解、多驻点。降级：局部非线性。
- **linear_program**：scipy.optimize.linprog(HiGHS) / cvxpy / OR-Tools。
  报告：最优值、对偶界。失败：约束矩阵病态。降级：无。
- **quadratic_program / convex_program**：cvxpy，先过 DCP 检查。
  报告：凸性论证（Hessian/组成规则）。失败：DCP 不过=模型非凸，如实降级。
- **milp**：OR-Tools MILP / scipy.milp。报告：MIP gap、节点数、时间限制。
- **cp_sat**：OR-Tools CP-SAT。报告：可行性证明或 gap。适合调度、覆盖、逻辑约束。
- **dynamic_programming**：自写 numpy。报告：状态空间大小、复杂度 O(状态×决策)。
- **shortest_path_flow**：scipy.sparse.csgraph / networkx / min-cost-flow。
  报告：精确最优。失败：负环。
- **statistical_inference**：statsmodels/scipy.stats。报告：CI、检验统计量与前提核查。

## local / global 家族

- **local_nonlinear**：SLSQP / trust-constr，多起点(≥8)。
  报告：best-of-N、起点列表、局部性声明。失败：停滞不可行点。
- **global_nonlinear**：differential_evolution / shgo / branch-and-bound 类。
  报告：搜索界内最优、种子策略。

## heuristic / surrogate 家族（最后手段）

- **evolutionary**（pymoo/GA/PSO）：仅当 exact/local/global 全不可行。
  **强制报告**：lower/upper bound、optimality gap、收敛曲线、≥5 seeds 均值±std、运行时间。
  无 gap 报告的启发式结果不得作为最终答案主张。
- **tsp_vrp**：OR-Tools routing + 2-opt/3-opt；n≤20 用 Held-Karp 精确对照。
- **bayesian_optimization**（Optuna TPE）：每 trial 入 run registry。
- **surrogate_optimization**：声明 kernel 与采集函数。
- **simulation_optimization**：公共随机数 + 复制数声明。

## 降级链总则

exact → (规模爆炸) relaxation/bound → (仍不可行) local multi-start → (仍不行) heuristic。
每级降级都要写进 SOLVER_STRATEGY.md 与实验记录，禁止静默降级。
