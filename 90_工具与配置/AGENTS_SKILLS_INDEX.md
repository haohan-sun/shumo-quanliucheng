# Skill 与 Agent 总索引

> 2026-09-05 盘点。本文件是导航目录，**不是**任何 skill/agent 的定义；
> 权威定义永远在各文件自身。修改定义请直接改对应文件，并同步本索引。

## 一、体系结构

```
AGENTS.md（最高路由规则）
  └─ configs/auto-routing.yaml（意图→Skill→Agent 路由表）
       └─ mm-orchestrator（总调度：分类任务、选 Skill、派 Agent、守 Gate）
            ├─ .agents/skills/   22 个项目技能（21 个 mm-* + context-optimization）
            ├─ .codex/agents/    11 个子代理（read-only / workspace-write 泳道）
            ├─ .codex/hooks.json  生命周期钩子（状态校验、元数据、溯源）
            └─ configs/           风格与布局规范
```

调度原则：每个非平凡任务由 mm-orchestrator 路由；写者唯一（同一 artifact
不并发两个写者）；读者（researcher/critic/reviewer/compliance）只读并行；
G1–G7 七个人工门禁只能由人批准，任何 Skill/Agent/测试不得代批。

## 二、项目技能（.agents/skills/，22 个）

按竞赛生命周期 S0→S15 排列（≈各技能负责阶段）：

| 技能 | 阶段 | 触发要点 | 主要产出 |
| --- | --- | --- | --- |
| mm-preflight | S0 | 新会话/阶段陈旧/环境检查 | 状态体检、输入清单 |
| mm-evidence-retrieval | S1-S2 | 附件、数据、参数证据 | Evidence Passport |
| mm-literature-integrity | S2,S12 | 文献/引用/新颖性核验 | 引用真实性记录 |
| mm-problem-analysis | S2b | 问题拆解、量纲、假设账本 | PROBLEM_ANALYSIS.json |
| mm-data-audit | S2c | 数据质量、泄漏、预处理边界 | 数据审计与预处理契约 |
| mm-route-tournament | S3-S4 | ≥2 条候选路线对比（G2 前） | 路线评审报告 |
| mm-mathematical-derivation | S5 | 已选路线的方程、目标、约束、初边值与独立检查 | MODEL_DERIVATION.md |
| mm-model-spec | S5-S6 | G2 后起草/校验 MODEL_SPEC | 模型规范（G3 冻结对象） |
| mm-solver-strategy | S6b | G3 后 exact-first 求解组合 | SOLVER_STRATEGY.md |
| mm-implementation | S7-S8 | G3 后实现基线+测试 | src/ 代码、equation-to-code 映射 |
| mm-experiment-optimization | S9 | G4 后优化/消融/灵敏度/稳健 | 实验注册表、结果 |
| mm-validation-uq | S9b | G4 后独立验证/UQ | 验证计划、UQ 报告 |
| mm-reproducibility | S7-S13 | 正式计算、图、论文数字追溯 | run manifest、哈希与复现命令 |
| mm-scientific-visualization | S11 | G5 后正式图（Figure Contract） | figures/ + manifest（G6 前） |
| mm-paper-writing | S12 | 从注册结果**撰写**论文章节 | 04_论文与提交/paper/ 草稿 |
| mm-cumcm-paper-writing-review | S12-S13 | CUMCM 专项写作、摘要与证据化评审 | 论文草稿或评审报告 |
| mm-paper-defense | S12-S13 | 成稿交叉审计/答辩问题 | 一致性审计报告 |
| mm-result-audit | S10,S13 | 结果有效性/复现审计 | 审计发现（只读） |
| mm-compliance | S14 | G6 后提交合规/匿名/AI 声明 | 合规检查单（G7 前） |
| mm-ai-provenance | 跨阶段 | AI 使用溯源记录（sidecar） | AI 使用报告 |
| mm-orchestrator | S0-S15 | 每个非平凡请求的总入口 | 调度与综合 |
| context-optimization | 工具型 | 上下文预算/降本策略 | 效率策略建议 |

支持文件：`mm-paper-writing/references/section_playbook.md`（通用逐节写作指南），
`mm-mathematical-derivation/references/methodology-sources.md`（推导方法来源），以及
`mm-cumcm-paper-writing-review/references/`（仓库所有者原创的 CUMCM 专项资料）。

## 三、子代理（.codex/agents/，11 个）

| 代理 | 沙箱 | 职责 | 禁止事项 |
| --- | --- | --- | --- |
| researcher | read-only | 附件/数据/文献证据泳道，可并行 | 写工件、选最终模型 |
| critic | read-only | 对抗性评审路线/假设/可识别性 | 选模型、改工件、批门禁 |
| implementer | workspace-write | G3 后唯一写者：基线+测试 | 改数学定义（需 MODEL_CHANGE_REQUEST） |
| deriver | workspace-write | G2 后唯一写者：可审计数学推导 | 选最终路线、写实现、改冻结规格 |
| optimizer | workspace-write | G4 后唯一写者：实验/调优/消融 | 为指标改数学问题 |
| visualizer | workspace-write | G5 后唯一写者：正式图+manifest | 编造数据、批 G6 |
| reviewer | read-only | 写后独立审计（代码/结果/图/论文） | 改被审工件、批门禁 |
| compliance | read-only | G6 后合规预检（BLOCKER/WARNING/INFO） | 改论文、打包、批 G7 |
| validator | read-only | 独立检验泛化、泄漏、UQ 与统计主张 | 调参、改结果、批门禁 |
| replicator | read-only | 校验 run 输入/代码/输出哈希与复现证据 | 改源文件或 run、批门禁 |
| judge | read-only | 按既定 rubric 裁定有限预算路线证据 | 新造路线、选最终模型、批 G2 |

写者交接链：deriver → critic/reviewer → MODEL_SPEC → implementer → reviewer → optimizer → reviewer → visualizer → reviewer。

## 四、配置与规范（configs/）

- `auto-routing.yaml`：意图→技能→代理路由表（权威）。
- `contest.yaml`、`workspace-layout.yaml`：赛项参数与目录布局。
- `CODE_STYLE.md`：竞赛代码风格规范（新增 2026-09-05）。
- `VISUAL_STYLE_GUIDE.md`：唯一视觉规范源；`画图SKILL.md` 仅是 legacy 参考，
  `src/viz/README.md` 与 `CODE_STYLE.md` 仅说明实现方式。

## 五、客户端级插件技能（非项目路由，仅供参考）

browser-use、computer-use、document-skills（docx/pdf/pptx/xlsx）、
skill-creator、zcode-guide 系列属于外部客户端插件，安装位置由客户端决定，
不参与 mm-* 路由；论文排版可借用 document-skills:docx/pdf，技能编写可借用
skill-creator。

## 六、运行保障

- `auto-routing.yaml` 已接入五项新增能力及 `mm-paper-writing`；无可靠命中时回退
  orchestrator，不猜测专业 Skill。
- `package_guard.py` 在创建归档前拒绝任意层级 locked cache、内部状态、链接、
  绝对路径和路径穿越；规则来自 `artifact_boundaries.yaml`。
- `artifact_state.py` 用内容哈希令修改后的 G3-G7 PASS 及下游 PASS 失效；只有现存
  的人工批准记录可生成新快照。
- `run_record.py` 与 `claim_registry.py` 建立输入/代码/配置/输出→run→论文 claim 链；
  `evals/workflow_benchmark.py` 提供轻量 routing/role/guard 基准。
