---
name: mm-problem-analysis
description: "AUTO TRIGGER: after evidence retrieval establishes inputs and before route tournament, when a problem must be decomposed into subproblems, task types, variables, objectives, constraints, scales, units, data/output requirements, assumption ledger, identifiability risks, hidden requirements, and terminology. DO NOT TRIGGER: route comparison, MODEL_SPEC drafting, data quality screening (mm-data-audit), or implementation. STAGE: S2b between evidence and route tournament. INPUTS: problem statement, attachments inventory, evidence passports. OUTPUTS: machine-readable PROBLEM_ANALYSIS.json validated by scripts/problem_analysis.py. BOUNDARIES: analysis only; never choose the final model or approve Gates."
---

# MM Problem Analysis

把赛题翻译成结构化的问题定义。产物是 `03_建模工作区/problem/PROBLEM_ANALYSIS.json`，
必须通过
`python 90_工具与配置/scripts/problem_analysis.py --check 03_建模工作区/problem/PROBLEM_ANALYSIS.json`
（`--check` 需要一个路径参数），后续 route tournament、model spec、data audit 全部以它为输入。

## 流程

1. **通读与术语**：定义题目术语（terminology），标记所有隐含要求
   （hidden_requirements：格式、单位、提交内容、评审暗示）。
2. **子问题拆解**：拆成可独立验证的子问题（subproblems），写明依赖关系（无环）。
3. **本质分类**：每个子问题标注任务类型（decision / prediction / optimization /
   simulation / inference / evaluation / allocation / scheduling / network / control）。
4. **变量与量纲**：决策变量、状态变量、外生变量，全部带单位与定义域。
5. **目标与约束**：目标（sense 必填）与约束（source = problem / derived / assumption）；
   边界条件、时间尺度、空间尺度单独记录。
6. **需求清单**：data_requirements（含 available 与 locator）、output_requirements、
   evaluation_metrics（对齐题目判分口径）。
7. **假设账本**：每条假设记 basis 与 strength（weak/moderate/strong）；
   weak 假设必须出现在后续 sensitivity 计划里。
8. **可识别性风险**：参数不可辨识、数据不足、目标冲突等，标 severity 与 mitigation。
9. **校验**：运行
   `python 90_工具与配置/scripts/problem_analysis.py --check 03_建模工作区/problem/PROBLEM_ANALYSIS.json`；
   PASS 后才能进入 route tournament。

## 红线

- 单位缺失的变量、无 sense 的目标、循环依赖 = 不合格 artifact。
- 本技能不做建模选择；发现多条可行路线时留给 mm-route-tournament。
