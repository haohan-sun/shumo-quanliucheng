# GitHub 架构调研（2026-09-05）

> 设计历史参考，非运行时配置、非 Skill discovery 来源；当前行为以
> `configs/auto-routing.yaml`、各项目 Skill 和可执行测试为准。

调研方法：网络检索 + 仓库结构阅读，提取设计思想而非复制文字/代码。
许可原则：思想借鉴不受版权限制；任何代码级借鉴仅来自宽松许可（MIT/Apache）项目，
且本项目全部为独立重写，无逐行复制。AGPL 项目只做思想级参考。

## 逐仓库结论

| repository | feature | why_useful | adopt | reject | adaptation | license | local_target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SakanaAI/AI-Scientist-v2 | agentic tree search（best-first 分支扩展 + experiment manager 分配预算）+ VLM 审稿 | 线性流水线会锁死在首路线；树搜索 + 廉价预筛把算力留给幸存路线 | 树状路线搜索、节点状态机、探索预算、manager 分配算力 | 自动生成 idea 不适合竞赛（题目固定）；端到端无人工门禁 | 改为"人提名路线 + 有限 beam 扩展"，预算以 quick-test 次数计 | MIT | mm-route-tournament（scripts/route_tree.py） |
| SamuelSchmidgall/AgentLaboratory | phased workflow（literature→plan→code→paper），agent 角色窄化 | 证明"窄角色 + 阶段交接"比全能 agent 稳定 | 角色窄化、阶段交接产物清单 | 它的 copilot 依赖与人工强交互 | 与现有 G-gate 串联，交接物即 schema 化 artifact | MIT | agent toml 定义（已有结构微调） |
| Future-House/paper-qa | evidence-first 引用：先定位原文证据再生成带引主张 | 直接对应"论文数字必须可追溯"红线 | claim→evidence 映射、引文可信度分级 | 它的向量库依赖较重 | 轻量化为 claim_registry.jsonl + supporting_run_ids | Apache-2.0（思想级） | scripts/claim_registry.py |
| XiangJinyu/AFlow_ | workflow 以可验证分数做 MCTS/扩展剪枝 | "分数驱动结构搜索"可用于路线评估 | 用可验证指标给路线节点打分 | 完整 MCTS 对 72h 竞赛过重 | 退化为 beam + 预算上限 | 设计思想级（未逐条核证许可，未复制代码） | mm-route-tournament |
| jihe520/MathModelAgent | 建模手/代码手/论文手分工、本地代码执行器、可直接提交产物 | 与本项目角色划分高度同构，验证了方向 | 本地可执行 + 产物直达提交包的思路 | **AGPL-3.0：不引用任何代码**；其"一键全自动"与本项目人工门禁相悖 | 仅借鉴角色划分与产物形态 | AGPL-3.0（思想级，零代码） | 已有 agent 结构（确认，不改动） |
| optuna/optuna | trial 记录、存储后端、study 比较 | 实验可比性需要统一 record | run registry 字段设计（params/metrics/state/datetime） | 分布式存储后端过重 | 单文件 JSONL/CSV registry | MIT | 03_建模工作区/runs/ + scripts/run_record.py |
| facebookresearch/hydra | 配置分层覆盖 + 可复现 job dir | run 目录内带生效配置是复现关键 | run_dir 内固化 resolved config | OmegaConf 依赖与 override DSL | 用纯 dict + JSON 固化 | MIT | scripts/run_record.py |
| IDSIA/sacred | experiment 元数据（host/deps/seeds/git dirty） | 字段清单直接对应复现需求 | git commit/dirty/依赖版本/host 采集 | MongoDB 观测端 | 落地为 run manifest 字段 | MIT | scripts/run_record.py |
| SALib/SALib | Sobol/Morris 采样与指数 | 灵敏度分析标准方法集 | 方法清单与选择规则（先 Morris 筛后 Sobol 精算） | 预算内不强制引入依赖：无则用 OAT+bootstrap 降级 | 依赖可选（try-import） | BSD-3 | scripts/validation_uq.py |
| cvxpy / Pyomo / OR-Tools / HiGHS / pymoo | 求解器生态 | solver portfolio 的"库存清单" | 按 problem class 建立优先级 portfolio（exact 优先） | 预装全部求解器 | 只探测可用性，缺失时降级链 | Apache-2.0/BSD-3 等（各自声明） | scripts/solver_strategy.py |
| HypothesisWorks/hypothesis | property-based testing | 数学不变量测试（如对称性、单调性） | 在 evals/tests 中对纯函数用不变量断言 | 对 agent 行为不适用 | 手写小型 property 用例 | Apache-2.0（思想级） | 90_工具与配置/tests/ |
| XiaoMaColtAI/yushui2022/handsomeZR-netizen/Lupynowinsixtdreanight 等数模 skill 合集 | prompt 模板、论文句式、图表选型清单 | 社区常见坑清单（图表滥用、摘要空洞） | 图表选型约束、评审 checklist 条目 | 大多为纯 prompt 堆砌，无 gate/复现机制——**reject 主体** | 有价值的 checklist 条目并入相关 SKILL references | 各异（未核证，未复制文字） | references/ 文档 |

## 汇总：采用的核心设计

1. **树状路线搜索 + 预算分配**（AI-Scientist-v2/AFlow）：route 节点字段 + quick-test 剪枝 + beam 宽度上限。
2. **角色窄化 + 读写泳道**（AgentLaboratory）：已有 7 agent 结构保留，新增 validator/replicator/judge 三个只读泳道。
3. **claim→evidence 追溯**（paper-qa）：claim_registry.jsonl，关键数字必须挂 run_id。
4. **run manifest 元数据集**（sacred/hydra/optuna）：run_id/git/deps/seeds/输入输出哈希/父 run。
5. **exact-baseline 优先的 solver portfolio**（优化器生态 + 竞赛经验）。
6. **错误学习与渐进加载**（AI-Scientist 失败模式分析）：error registry 按类别检索，不整包入上下文。

## 明确拒绝的设计

- 全自动无门禁科研流水线（与人工 G-gate 制度冲突，竞赛诚信风险）。
- 完整 MCTS/LLM-judge-only 的自动验收（评分必须含确定性校验器）。
- 重型依赖（向量库/数据库/OmegaConf）——轻量本地实现足够。
- AGPL 项目的任何代码（法律隔离）。
