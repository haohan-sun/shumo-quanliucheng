# AUTO-ORCHESTRATED MODE

## 最高级路由规则

For every non-trivial project task:

- inspect `run-manifest.json`, `03_建模工作区/decisions/DECISION_LOG.md`, and project status first;
- route through `mm-orchestrator` before specialist execution;
- automatically select the single best-matching project Skill and any necessary review Skill;
- automatically delegate genuinely independent work to specialized subagents;
- automatically run relevant validation and material-AI provenance checks;
- do not require manual Skill or Agent invocation unless automatic routing fails;
- stop at every Human Gate and request an explicit human decision;
- never auto-approve, infer, or fabricate a Human Gate approval.

Simple navigation, literal file lookup, and one-line status questions do not require specialist
routing. All modeling, evidence, implementation, experiment, visualization, audit, paper, and
submission work is non-trivial.

`mm-orchestrator` only inspects state, classifies the task, determines the stage, selects Skills,
delegates subagents, checks dependencies, manages Gates, and synthesizes results. It must not
perform all specialist work itself or choose the final mathematical model.

## 自动路由表

| Natural-language intent | Primary Skill | Primary Agent | Optional independent review |
| --- | --- | --- | --- |
| inputs, attachments, data facts, parameter evidence | `mm-evidence-retrieval` | `researcher` | `critic` for disputed assumptions |
| literature, paper search, citation, novelty | `mm-literature-integrity` | `researcher` | `critic` or `reviewer` when claims are material |
| problem decomposition, units, assumptions, requirements | `mm-problem-analysis` | `researcher` | `critic` |
| data quality, leakage, preprocessing contract | `mm-data-audit` | `researcher` | `validator` |
| human-nominated route comparison | `mm-route-tournament` | `critic` + `researcher` | stop at G2 |
| selected-route mathematical derivation | `mm-mathematical-derivation` | `deriver` | `critic` + `reviewer` |
| approved model contract drafting/checking | `mm-model-spec` | `critic` for read-only checks | stop at G3 |
| frozen model solver portfolio | `mm-solver-strategy` | `researcher` | `critic` |
| approved model implementation or baseline | `mm-implementation` | `implementer` | `reviewer` |
| approved baseline optimization, ablation, benchmark | `mm-experiment-optimization` | `optimizer` | `reviewer` |
| validation, UQ, calibration, robustness evidence | `mm-validation-uq` | `optimizer` | `validator` + `replicator` |
| important run or paper-number traceability | `mm-reproducibility` | `replicator` | read-only replication |
| figure, plot, visual design from registered results | `mm-scientific-visualization` | `visualizer` | `reviewer` |
| consistency, bug, result validity, reproducibility | `mm-result-audit` | `reviewer` + `critic` | both read-only |
| paper/defense cross-artifact audit | `mm-paper-defense` | `reviewer` | `critic` when claims are debatable |
| paper drafting or polishing from registered evidence | `mm-paper-writing` | one assigned writer | `reviewer` + `validator` + `replicator` |
| CUMCM-specific paper writing or evidence-based review | `mm-cumcm-paper-writing-review` | one assigned writer | `reviewer` + `validator` + `replicator` |
| submission, anonymity, AI disclosure | `mm-compliance` | `compliance` | stop at G7 |
| material AI-use recording/report generation | `mm-ai-provenance` | main orchestrator | no raw chain-of-thought |

The canonical machine-readable table is `90_工具与配置/configs/auto-routing.yaml`.

## Human Gates

The following Gates require an explicit human instruction and an approval record in
`run-manifest.json`: G1 problem selection, G2 model/method selection, G3 MODEL_SPEC freeze,
G4 baseline approval, G5 final method/results freeze, G6 final figure approval, and G7
ready-to-submit. Agents, Skills, tests, and Hooks may report readiness but may not pass a Gate.

## Subagent ownership

Parallelize independent read-heavy research, criticism, and review. Assign exactly one writer per
artifact. Never run `implementer`, `optimizer`, or `visualizer` concurrently against the same file
or truth source. Read-only subagents return evidence to the parent; the parent synthesizes and
records the accepted result.

## Skill discovery

Only project-owned `mm-*` Skills under `90_工具与配置/.agents/skills/` participate in project
routing. `90_工具与配置/third_party/references/` is reference-only and is never an active Skill
discovery root. A specialist may read a selected third-party reference only when its scoped task
requires it.

## Lifecycle automation

Project Hooks may validate state, refresh status, record subagent/tool metadata, and check
provenance. Hooks must not select models, change mathematical definitions, approve Gates, or
record hidden chain-of-thought. Submission provenance groups material use into a small number of
categories rather than exposing the full dispatch trace.

# 工作区边界

本项目按职责分区，后续任何 Agent 或脚本都必须写入正确区域：

- `01_题目与要求/`：官方题目、附件、说明和格式规范；视为只读源文件。
- `02_参考文献/`：用户提供的论文与阅读资料；不得混入生成结果。
- `03_建模工作区/`：模型、正式代码、测试、数据处理、实验、结果和图表。
- `04_论文与提交/`：论文正文、引用库、AI 使用说明和最终提交包。
- `90_工具与配置/`：Agent、Skill、脚本、配置、Schema 和工具报告。

正式代码只能写入 `03_建模工作区/src/`，正式论文只能写入
`04_论文与提交/paper/`。不得把比赛成果写进 `90_工具与配置/`。

根目录 `.agents` 与 `.codex` 是隐藏的发现入口，分别指向
`90_工具与配置/.agents` 和 `90_工具与配置/.codex`。当任务与某个
`mm-*` Skill 匹配时由 orchestrator 自动调用，但核心模型与人工 Gate 仍由参赛者确认。

统一使用根目录 `run.ps1` 执行状态、校验、哈希和提交检查。忽略名称以
`~$` 开头的 Office 锁文件，不把缓存或临时渲染物当作正式成果。

## AUTO ROUTING
For every non-trivial request, automatically use the relevant installed project skills and custom subagents; never ask the user to invoke them manually.

Route by intent:
literature/evidence/novelty -> researcher + relevant research skills
method criticism -> critic
mathematical derivation -> deriver + critic/reviewer
implementation -> implementer
optimization/experiments -> optimizer
figures -> visualizer
review/audit -> reviewer
CUMCM paper writing/review -> mm-cumcm-paper-writing-review
submission/compliance -> compliance

Use only agents/skills relevant to the current task. Parallelize independent read-only work; avoid concurrent writers on the same artifact.

Human approval is mandatory for: problem selection, method selection, MODEL_SPEC freeze, baseline approval, final results/method, final figures, and submission. Never auto-approve these gates.
