---
name: mm-route-tournament
description: "AUTO TRIGGER: humans have nominated at least two candidate modeling routes and request comparison, bounded route-tree/beam exploration, stress-testing, risks, fallbacks, or falsification. DO NOT TRIGGER: free-form model invention, final route selection, MODEL_SPEC drafting after G2, implementation, or optimization. STAGE: S3-S4 between G1 and G2. INPUTS: human candidates, evidence, constraints, evaluation criteria and fixed exploration budget. OUTPUTS: bounded route tree, quick-test evidence, comparison matrix and G2 decision material. BOUNDARIES: researcher/critic/judge are read-only; orchestrator records tree state; stop at G2 and never choose the final route."
---

# MM Route Tournament

Evaluate only human-nominated routes. Produce a comparable record of assumptions, data needs,
identifiability, feasibility, risks, validation plans, fallbacks, and falsification conditions.
Present tradeoffs to humans and stop before G2.

## 路线树搜索（v2）

在平面评分之外，用**预算制 beam/tree search** 组织候选路线
（借鉴 AI-Scientist-v2 / AFlow 的树搜索与分数剪枝思想，轻量实现）：

1. **建树**：`python 90_工具与配置/scripts/route_tree.py --tree 03_建模工作区/decisions/route-tree.json --init problem-id`。
   人类提名的路线为 depth-0 根节点；每个节点记录 parent、hypothesis、model_family、
   preprocessing、objective、constraints、solver、complexity、evidence、novelty、
   expected_score、risk、failure_condition、experiment_cost、status。
2. **生命周期**：generated → reviewed → quick_tested；随后可 pruned、revised 或在人工 G2 后 promoted。
   review = critic 对节点假设/可识别性/风险的对抗审查；revise 仅限未扩展叶节点，清空旧实测分数，必须重新 reviewed → quick_tested。
3. **廉价快测**：先用小样本/短时长 quick-test（子采样拟合、小规模求解、
   简化算例）给 quick_test_score，再谈扩展。快测预算默认 8 次（budget.max_quick_tests）。
4. **剪枝与预算**：默认预算 max_nodes=16、max_depth=3、beam_width=4；
   `prune_below_beam` 每层只留 beam 宽度内的幸存者，非幸存者必须留 prune_reason。
   根深度为0，最大允许深度为3；节点及快测预算累计消耗，剪枝不退预算。
   只有 quick_tested beam 幸存节点可以扩展；每层未测试节点必须先测试或给出理由显式剪枝。
   排名依次为实测分数、预期分数、较小试验成本、稳定 route_id。计算预算（真实实验）只分给幸存路线。
5. **收敛**：到达 max_depth 或预算耗尽后，把 beam 内 top 路线的对比矩阵、
   tradeoffs、风险与 fallback 提交给人工 G2。`promote` 只在人工批准后执行，
   必须读取 run manifest 中已批准的 G2（approved_by 为人、approved_at 可解析，并明确绑定 problem_id 与 route_id）；本脚本不写 Gate。
   其余存活路线自动置 pruned（reason="lost to promoted route"），树关闭后拒绝新增、review、revise 等修改。
6. **产物**：树 JSON 存 `03_建模工作区/decisions/route-tree.json`
   （连字符命名；`gate_control.py` 与 `auto-routing.yaml` 都按此路径解析）；
   失败路线的教训写入 error registry（category=math/solver/data 等）。

红线：预算字段不可为绕过检查而调大——确需扩大，向人工说明并记录决策；
本技能始终不代替人工选择最终路线。

## 调用与证据接入

orchestrator 将候选只读材料分别交 researcher 和 critic；judge 在相同评价准则下只读比较，返回证据和建议，不产生 G2 approval。
主调度器是 route-tree.json 唯一 writer。快测使用已有执行器的短预算运行，先记录 reproducibility run_id、参数、seed、输入/代码 hash，再把 evidence 中的报告路径关联到节点。
`record_quick_test` 只登记已执行的实测结果，不自行运行模型，也不把 expected_score 冒充实测值。
失败条件与剪枝原因提供给 error registry；最终比较材料关联 claim registry，未过 G2 的候选不得成为正式方法声明。

CLI 支持 `--action add|review|quick-test|revise|prune|beam|promote --payload <json>`；payload 为同名 Python 函数除 tree 外的关键字参数。
例如 add 包含 hypothesis/model_family/solver，review 包含 route_id/risk/expected_score，quick-test 包含 route_id/score，beam 包含 depth。
promote 额外要求 `--manifest run-manifest.json`，无有效人工记录时失败；`--stats <tree.json>` 只读检查计数。
运行 `python -m pytest 03_建模工作区/tests/test_route_tree.py` 验证预算、生命周期、beam、G2阻断和 CLI。
