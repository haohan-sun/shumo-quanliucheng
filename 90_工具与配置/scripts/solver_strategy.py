"""Solver strategy: classify problem structure -> ordered solver portfolio (exact first).

The decision table is the source of truth; heuristics (evolutionary etc.) are a
LAST resort and must report optimality gap, convergence, and seed variation.

CLI:
    python .../solver_strategy.py --classify "minimize linear cost subject to linear constraints, binary decisions"
    python .../solver_strategy.py --probe
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

PORTFOLIO: dict[str, dict[str, Any]] = {
    "closed_form": {"family": "exact", "tools": ["sympy", "numpy.linalg"], "note": "prefer when the stationarity conditions are tractable"},
    "linear_program": {"family": "exact", "tools": ["scipy.optimize.linprog (HiGHS)", "cvxpy", "OR-Tools"], "note": "LP duality gives bounds for free"},
    "quadratic_program": {"family": "exact", "tools": ["cvxpy", "scipy.optimize"], "note": "verify convexity before claiming global optimum"},
    "convex_program": {"family": "exact", "tools": ["cvxpy"], "note": "DCP check must pass"},
    "milp": {"family": "exact", "tools": ["OR-Tools CP-SAT/MILP", "scipy.optimize.milp (HiGHS)", "cvxpy+solver"], "note": "report MIP gap and runtime"},
    "minlp": {"family": "hybrid", "tools": ["pyomo+solver", "scipy + rounding heuristic"], "note": "exact only if global solver available; else report bounds"},
    "cp_sat": {"family": "exact", "tools": ["OR-Tools CP-SAT"], "note": "combinatorial feasibility/scheduling with logical constraints"},
    "dynamic_programming": {"family": "exact", "tools": ["custom (numpy)"], "note": "check state-space size; curse of dimensionality"},
    "shortest_path_flow": {"family": "exact", "tools": ["scipy.sparse.csgraph", "networkx", "OR-Tools"], "note": "Dijkstra/SPFA/min-cost-flow"},
    "tsp_vrp": {"family": "hybrid", "tools": ["OR-Tools routing", "2-opt/3-opt local search"], "note": "exact only for small n (Held-Karp <= ~20); report gap vs LB"},
    "local_nonlinear": {"family": "local", "tools": ["scipy.optimize.minimize (SLSQP/trust-constr)"], "note": "multi-start required; report best-of-N and localness"},
    "global_nonlinear": {"family": "global", "tools": ["scipy.optimize.differential_evolution", "scipy.optimize.shgo"], "note": "verify with bounds; deterministic seed policy"},
    "evolutionary": {"family": "heuristic", "tools": ["pymoo", "scipy.optimize.differential_evolution"], "note": "ONLY when exact/local/global infeasible; MUST report gap/LB-UB, convergence curves, seed variation"},
    "bayesian_optimization": {"family": "surrogate", "tools": ["Optuna (TPE/sampler)", "scikit-optimize"], "note": "expensive black-box; log every trial into run record"},
    "simulation_optimization": {"family": "surrogate", "tools": ["Optuna + simulator", "replication + common random numbers"], "note": "variance reduction before comparing designs"},
    "surrogate_optimization": {"family": "surrogate", "tools": ["sklearn GP + acquisition"], "note": "state kernel and acquisition explicitly"},
    "statistical_inference": {"family": "exact", "tools": ["statsmodels", "scipy.stats"], "note": "report CIs; bootstrap for nonstandard statistics"},
    "forecasting": {"family": "local", "tools": ["statsmodels (ARIMA/ETS)", "sklearn baselines"], "note": "rolling-origin backtest mandatory; naive/seasonal-naive baseline mandatory"},
    "monte_carlo_simulation": {"family": "simulation", "tools": ["numpy rng"], "note": "seed policy + CI via batch means/bootstrap"},
}

_STRUCT_RULES: list[tuple[str, str]] = [
    (r"integer|binary|0-1|离散|整数|01变量", "milp"),
    (r"tsp|vrp|旅行商|车辆路径|配送路径", "tsp_vrp"),
    (r"shortest path|最短路径|network flow|最大流|min.?cost flow|网络流", "shortest_path_flow"),
    (r"schedule|调度|timetable|排班|排序作业", "cp_sat"),
    (r"dynamic program|动态规划|stage decision|多阶段决策", "dynamic_programming"),
    (r"linear (objective|constraints)|线性规划|线性目标.*线性约束", "linear_program"),
    (r"quadratic|二次", "quadratic_program"),
    (r"convex|凸优化", "convex_program"),
    (r"nonlinear|非线性|non.?convex", "global_nonlinear"),
    (r"simulation|仿真|蒙特卡洛|monte carlo|排队|queue", "monte_carlo_simulation"),
    (r"forecast|预测|time series|时间序列|arima", "forecasting"),
    (r"regression|回归|significan|假设检验|hypothesis|置信|confidence", "statistical_inference"),
    (r"expensive|black.?box|黑箱| costly |昂贵的?仿真", "bayesian_optimization"),
    (r"multi.?objective|多目标|pareto|帕累托", "evolutionary"),
]


def classify(description: str) -> list[str]:
    """Return candidate problem classes (most specific first)."""
    text = description.lower()
    classes: list[str] = []
    for pattern, cls in _STRUCT_RULES:
        if re.search(pattern, text) and cls not in classes:
            classes.append(cls)
    if not classes:
        classes = ["local_nonlinear"]
    return classes


def portfolio_for(classes: list[str]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for cls in classes:
        entry = PORTFOLIO[cls]
        ordered[cls] = entry
    exact = [c for c in classes if PORTFOLIO[c]["family"] in {"exact"}]
    ordered["policy"] = {
        "exact_first": True,
        "require_exact_or_relaxation_baseline": bool(exact),
        "heuristic_reporting_duties": ["lower/upper bound", "optimality gap", "convergence curve", "seed variation (>=5 seeds)", "runtime"],
    }
    return ordered


def probe_available() -> dict[str, bool]:
    """Detect which portfolio tools import successfully in this environment."""
    probes = {
        "numpy": "numpy", "scipy": "scipy", "cvxpy": "cvxpy", "pymoo": "pymoo",
        "optuna": "optuna", "ortools": "ortools", "pyomo": "pyomo",
        "statsmodels": "statsmodels", "networkx": "networkx", "sympy": "sympy",
    }
    import importlib.util
    return {name: importlib.util.find_spec(module) is not None for name, module in probes.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Solver strategy decision helper.")
    parser.add_argument("--classify", metavar="DESCRIPTION")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe_available(), indent=2))
        return 0
    if args.classify:
        classes = classify(args.classify)
        print(json.dumps({"classes": classes, "portfolio": portfolio_for(classes)},
                         ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
