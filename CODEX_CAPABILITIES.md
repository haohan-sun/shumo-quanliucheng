# Codex Capabilities

更新日期：2026-09-16  
范围：当前完整数学建模工作区  
状态：AUTO-ORCHESTRATED，11 Agents，22 Skills。

## 自动调度

- 根 `AGENTS.md`：所有非简单项目任务先经 `mm-orchestrator`，自动选择相关 Skill 和 Agent。
- `.codex/config.toml`：`agents.enabled = true`，配置并发上限 7，Hooks 已启用。
- Human Gates：G1–G7 均需明确人类批准；Agent、Skill、Hook 和测试均不得自动批准。
- Writer 互斥：implementer、optimizer、visualizer 分域写入；同一核心 artifact 不得并发写。
- 第三方参考：`90_工具与配置/third_party/references/` 不参与 Skill discovery。

## Agents

| 名称 | 权限 | 用途 | 自动触发条件 | 自动调用 |
|---|---|---|---|---|
| researcher | read-only | 附件、数据、文献、参数证据 | 独立检索或证据任务 | 是，由 orchestrator 派发 |
| critic | read-only | 方法、假设、可辨识性与失败条件审查 | 方法批评、候选路线或反例检查 | 是 |
| reviewer | read-only | 实现、实验、结果、图、论文与复现审查 | writer 交接或 audit/review | 是 |
| compliance | read-only | 匿名、格式、文件、AI 披露检查 | G6 后或明确合规任务 | 是 |
| validator | read-only | 泛化、泄漏、校准、UQ 与统计主张独立检验 | 验证交接或明确统计审计 | 是 |
| replicator | read-only | run 输入/代码/输出哈希与复现证据检查 | 重要运行与论文数字交接 | 是 |
| judge | read-only | 按既定 rubric 裁定有限预算路线证据 | 路线锦标赛形成证据后 | 是 |
| deriver | workspace-write | 已选路线的数学推导、单位、初边值与独立检查 | G2 后、G3 前的推导任务 | 是，单 writer |
| implementer | workspace-write | 冻结模型实现、测试、baseline | G3 人工批准后的实现任务 | 是，单 writer |
| optimizer | workspace-write | 优化、消融、基准、敏感性、稳健性 | G4 人工批准后的实验任务 | 是，单 writer |
| visualizer | workspace-write | 可复现科学图与 Figure Contract | G5 人工批准后的画图任务 | 是，单 writer |

read-only/workspace-write 是 Codex runtime sandbox 权限，不是独立 NTFS ACL。

## Skills

| 名称 | 用途 | 自动触发条件 | 隐式调用 | 项目路由 | 来源/本地状态 |
|---|---|---|---|---|---|
| mm-orchestrator | 状态、分类、Gate、委派、汇总 | 每个非简单项目任务 | 是 | 默认路由器 | 项目本地，Git tracked |
| mm-preflight | 环境、输入、状态和 stale 检查 | 新阶段、环境或清单请求 | 是 | preflight | 项目本地，Git tracked |
| mm-evidence-retrieval | 附件、数据、事实、参数证据 | 有界 evidence/data 请求 | 是 | evidence | 项目本地，Git tracked |
| mm-literature-integrity | 文献、引用、DOI、创新性核验 | literature/citation/novelty | 是 | literature | 项目本地，Git tracked |
| mm-route-tournament | 比较人类候选方法 | G1 后多候选路线审查 | 是 | route_review | 项目本地，Git tracked |
| mm-problem-analysis | 问题拆解、变量、单位和假设账本 | 题意与需求分析 | 是 | problem_analysis | 项目本地，Git tracked |
| mm-data-audit | 数据质量、泄漏与预处理契约 | 建模前数据审计 | 是 | data_audit | 项目本地，Git tracked |
| mm-mathematical-derivation | 将已选路线推导为方程、目标、约束和初边值 | G2 后数学推导 | 是 | mathematical_derivation | 项目本地，Git tracked；方法来源见 Skill reference |
| mm-model-spec | 起草/检查权威 MODEL_SPEC | G2 后模型规范任务 | 是 | model_spec | 项目本地，Git tracked |
| mm-solver-strategy | 从冻结规格形成求解器组合 | G3 后求解策略 | 是 | solver_strategy | 项目本地，Git tracked |
| mm-implementation | 冻结模型代码、测试和 baseline | G3 后实现 | 是 | implementation | 项目本地，Git tracked |
| mm-experiment-optimization | 优化、消融、基准与稳健性实验 | G4 后优化/实验 | 是 | optimization | 项目本地，Git tracked |
| mm-validation-uq | 独立验证、敏感性、稳健性与不确定性量化 | G4 后验证 | 是 | validation_uq | 项目本地，Git tracked |
| mm-reproducibility | 运行清单、哈希和最小复现命令 | 重要计算、图和论文数字 | 是 | reproducibility | 项目本地，Git tracked |
| mm-result-audit | 结果一致性、约束、来源和复现 | validity/bug/audit | 是 | audit | 项目本地，Git tracked |
| mm-scientific-visualization | 从注册结果生成科学图 | G5 后 figure/plot | 是 | visualization | 项目本地，Git tracked |
| mm-paper-defense | 论文主张、结果映射与答辩审查 | 已有论文的跨 artifact 审查 | 是 | paper_audit | 项目本地，Git tracked |
| mm-paper-writing | 从注册证据撰写通用数模论文 | G5 后写作 | 是 | paper_writing | 项目本地，Git tracked |
| mm-cumcm-paper-writing-review | CUMCM 专项写作、摘要与证据化评审 | 明确 CUMCM/国赛论文任务 | 是 | cumcm_paper_writing_review | 仓库所有者原创，已做公开路径清理 |
| mm-compliance | 提交规则、匿名、格式、AI 披露 | G6 后 submission/compliance | 是 | compliance | 项目本地，Git tracked |
| mm-ai-provenance | 记录主要 AI 使用并生成报告 | material AI work sidecar | 是 | provenance | 项目本地，Git tracked |
| context-optimization | 上下文预算、遮蔽、缓存、分区、token 成本 | 上下文容量或成本成为约束 | 是 | 不进入数学建模 intent table | `muratcankoylan/Agent-Skills-for-Context-Engineering` @ `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`；3 个上游文件原样 tracked，`agents/openai.yaml` 为本地自动调用元数据 |

Skill 的 frontmatter、目录名与发现入口由发布验证统一检查；实时结果以仓库 README 的验证记录为准。

## Hooks

| Event | 行为 | 写入边界 | 状态 |
|---|---|---|---|
| SessionStart | 检查状态、结构和 contracts，加载状态摘要 | 机械状态时间与 session-status | 已配置 |
| SubagentStart | 记录最小启动 metadata | event-per-file provenance | 已配置 |
| SubagentStop | 记录最小停止 metadata | event-per-file provenance | 已配置 |
| Stop | 环境/结构/contracts/tests/provenance 校验 | 机械验证状态；不得改 Gate | 已配置 |

Hooks 不记录隐藏 chain-of-thought，不选择科研方法，不批准 Human Gate。

## 验收摘要

本文件描述能力边界，不保存可能过期的测试数字。发布前实际运行并记录：结构验证、
Skill 快速校验、自动路由测试、全量 pytest、敏感信息扫描和公开仓库可见性检查。
