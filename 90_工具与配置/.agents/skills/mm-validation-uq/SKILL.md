---
name: mm-validation-uq
description: "AUTO TRIGGER: G4 baseline approved, and the request is model VALIDATION, generalization, uncertainty quantification, calibration, stress testing, scenario robustness, Sobol/Morris screening, residual diagnostics, or seed robustness — as distinct from tuning. DO NOT TRIGGER: hyperparameter search/solver comparison/ablation aimed at improvement (mm-experiment-optimization), result audit of already-produced artifacts (mm-result-audit), or pre-G4 work. STAGE: S9b after mm-experiment-optimization and before G5. INPUTS: frozen MODEL_SPEC, baseline + tuned runs, data audit preprocessing contract. OUTPUTS: validation plan + UQ report in 03_建模工作区/experiments/validation/ with run records. BOUNDARIES: uses scripts/validation_uq.py; never reuse tuning runs as validation evidence; never approve G5."
---

# MM Validation & UQ

调参、验证、灵敏度、不确定性是四件不同的事，证据不得互借：

| 活动 | 问题 | 工具入口 |
| --- | --- | --- |
| parameter tuning | 哪组参数最好 | mm-experiment-optimization |
| model validation | 换数据还行吗 | holdout / rolling backtest |
| sensitivity analysis | 输出对哪输入敏感 | oat_sensitivity / morris_screening / SALib-Sobol |
| uncertainty quantification | 结果的不确定区间多大 | bootstrap_ci / Monte Carlo / calibration |

用同一批实验既调参又宣称可靠 = 违规（验证集已被调参污染）。

## 流程

1. **验证计划**：按问题类型选定协议并写入
   `03_建模工作区/experiments/validation/VALIDATION_PLAN.md`：
   - 预测类：train/valid/test 三分 + rolling-origin backtest（时间序列必须滚动），
     空间数据用 spatial holdout；naive/seasonal-naive 基线必报。
   - 推断类：残差诊断（residual_diagnostic 模板）、前提核查、bootstrap CI。
   - 仿真类：Monte Carlo 重复 + batch means CI + 公共随机数。
   - 全部类型：≥5 seeds 的 seed_robustness；分类/概率输出加 calibration_curve。
2. **执行**：工具函数一律来自 `90_工具与配置/scripts/validation_uq.py`
   （numpy 实现无重依赖；SALib 已装则可用 Sobol，否则 Morris 筛查足够）。
   每次执行用 `run_record.create_run/finalize_run` 落 runs/ 记录。
3. **灵敏度**：先 OAT（便宜、可解释、出龙卷风图），关键模型再 Morris（mu*排序），
   预算允许才上 Sobol（一阶/总效应指数）。弱假设（problem analysis 假设账本）
   必须在扫描范围内。
4. **压力测试**：极端场景（边界条件、最坏情形输入、约束临界）至少 3 组。
5. **报告**：结果 + 图（走 viz 模板）写入 `experiments/validation/`，
   数字全部可追溯 run_id；结论区分"调参后最优"与"验证后可靠"。

## 红线

- 验证数据参与过任何调参决策 = 证据作废，重新划分重跑。
- 单种子、无 CI、无基线的"稳定"主张 = 违规。
- 本技能不改模型、不调参、不批 G5。
