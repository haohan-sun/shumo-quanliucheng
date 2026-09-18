# 数模全流程

**Reproducible AI-assisted mathematical modeling workspace.**
面向数学建模竞赛与研究型项目的通用工作区：把材料、证据、推导、模型规范、代码、实验、
验证、图表、论文和提交检查放进同一条可追溯的流程，并保持每类成果的目录边界。

三条不可让步的原则：

- **AI 协助执行，人做决定。** 题目、模型、最终结果和提交由人决定；G1–G7 人工 Gate
  只能由人批准，任何 Agent、Skill、测试或 Hook 都不能代批。
- **正式数字必须可追溯。** 论文里的每个数字都要能沿
  `输入 → 代码 → 配置 → 运行记录 → 输出哈希 → 主张` 回溯。
- **solver success ≠ 模型正确。** 推导、实现、验证分开审查，通过测试不等于结论成立。

本公开版由 2026-09-05 的初始环境快照整理而成：不含赛题、行业案例、竞赛数据、实验结果
或论文成果，也没有旧私有仓库信息和本机绝对路径。

---

## 当前状态

- 核心工程与跨平台 CI 已稳定（Ubuntu/Windows × Python 3.11/3.13 全绿）。
- 这是一个**公开工作区模板**，不包含任何具体赛题、数据或竞赛成果；toy demo 是完全合成的。
- 下一阶段的重点是用不同类型的历史真题做真实回归测试，而不是继续扩展框架。

## 3 分钟 Quick Start

前置条件：**Python 3.11–3.13**（`pyproject.toml` 的 `requires-python` 是唯一权威）和
**git**。`uv` 可选；没有 `uv` 时会自动用 `pip`。

```powershell
# Windows (PowerShell)
git clone https://github.com/haohan-sun/shumo-quanliucheng.git
cd shumo-quanliucheng
.\setup.ps1
.\run.ps1 doctor
.\run.ps1 validate
```

```bash
# Linux / macOS
git clone https://github.com/haohan-sun/shumo-quanliucheng.git
cd shumo-quanliucheng
./setup.sh
./run.sh doctor
./run.sh validate
```

`setup` 会自动寻找满足 `requires-python` 的解释器、建立 `.venv`、安装依赖并跑一次
`doctor`。重复运行是幂等的；解释器换了用 `.\setup.ps1 -ForceRecreate` 重建。

`setup` 是唯一在 `.venv` 还不存在时就能运行的命令：`.\run.ps1 setup`（POSIX 下
`./run.sh setup`）会在解释器检查之前转发给 `setup.ps1` / `setup.sh`，所以第一次安装
两条路径都可用。

不想装完整依赖、只想先看结构：

```powershell
.\run.ps1 setup --dry-run          # 只打印计划，不做任何修改
.\run.ps1 setup --ci --no-doctor   # 只装必需依赖，跳过 doctor
.\setup.ps1 -DryRun                # 同样的功能，PowerShell 风格参数
```

## 最小 Demo：一个数字如何走完全程

`examples/toy_demo/` 是一个完全合成、无版权与隐私风险的玩具算例
（24 个点的指数衰减 + 未知偏置），用来在动真格之前把整条链路走一遍：

```powershell
.\run.ps1 demo
```

它按顺序产出：题目 → 数学推导 → 冻结 MODEL_SPEC → Gate 示例（**故意保持 pending**）→
tracked run（git 状态、输入/代码哈希、种子、依赖、输出、指标）→ 图形 manifest →
claim registry → 只引用已登记数字的论文片段。全部产物都在
`examples/toy_demo/build/` 下，不会碰 `03_建模工作区/`、`04_论文与提交/` 或
`run-manifest.json`。

重跑不必要，只想复核已有产物是否仍与运行记录一致：

```powershell
.\run.ps1 demo --check-only
```

## 核心工作流

```text
题目与附件
→ 证据检索 / 文献核验        mm-evidence-retrieval / mm-literature-integrity
→ 问题分析 / 数据审计        mm-problem-analysis / mm-data-audit
→ 候选路线比较（停 G2）      mm-route-tournament
→ 数学推导                   mm-mathematical-derivation
→ MODEL_SPEC（停 G3）        mm-model-spec
→ 求解策略 / 基线实现        mm-solver-strategy / mm-implementation
→ 优化实验                   mm-experiment-optimization
→ 独立验证与不确定性量化      mm-validation-uq
→ 科学制图                   mm-scientific-visualization
→ 论文写作与交叉审查          mm-paper-writing / mm-paper-defense
→ 匿名、AI 声明与提交检查      mm-compliance（停 G7）
```

`AGENTS.md` 与 `90_工具与配置/configs/auto-routing.yaml` 是权威路由表：自然语言请求由
`mm-orchestrator` 选择唯一主 Skill，并按需组织只读复核。直接用自然语言交代任务即可，
不需要手动点名 Skill。

混合了多类工作的复杂请求会先被拆成有限的 atomic task，再逐个交给同一个确定性 router：

```powershell
.\run.ps1 route "拆解题目、变量、单位和约束"        # 单任务路由预览
.\run.ps1 plan "审计数据缺失值并检验稳健性，同时出主结果图和摘要初稿"
```

`plan` 输出带依赖关系的 task DAG、每个 task 的 Skill/Agent、并行 wave、Gate 停止点，
以及 writer 冲突检查。它不会替任何人通过 Gate，也不会让两个 writer 同时写同一份产物。

## 为什么结果可追溯

| 环节 | 机制 | 产物 |
| --- | --- | --- |
| 输入固定 | 官方题目与原始数据哈希 | `run-manifest.json` → `input_hashes` |
| 每次正式计算 | tracked run 记录 git 状态、输入/代码/配置哈希、种子、依赖、命令、输出哈希、退出码、耗时 | `03_建模工作区/runs/<run_id>/manifest.json` |
| 图表绑定数据 | Figure Contract + manifest 绑定 run_id 与输出哈希 | `03_建模工作区/figures/manifest.json` |
| 论文数字绑定计算 | claim registry 把每句带数字的主张挂到成功的 run | `04_论文与提交/paper/claim_registry.jsonl` |
| 结果失效传播 | 已批准 Gate 依赖的产物一旦变化，该 Gate 及全部下游自动失效 | `90_工具与配置/state/artifact_snapshots.json` |

`claim_registry` 会拒绝只做登记、没有真实执行记录的 run 作为计算型主张的证据：
没有 git commit、没有代码哈希、没有输出哈希、没有实测耗时，或退出码非 0，都不算证据。

## Human Gates（G1–G7）

| Gate | 人的决定 | 绑定的产物 |
| --- | --- | --- |
| G1 | 选哪道题 | 选定的题目 |
| G2 | 采用哪套方法 | route id、problem id、路线树哈希 |
| G3 | 冻结模型规范 | `MODEL_SPEC.md` |
| G4 | 接受基线 | 基线 run 与指标 |
| G5 | 冻结最终方法与结果 | 结果登记表与 run id |
| G6 | 批准正式图 | 图表 manifest |
| G7 | 允许提交 | 整个提交包 |

```powershell
.\run.ps1 gates        # 只读查看 G1–G7 当前状态
```

批准只能由人显式下达，并用 `scripts/gate_control.py` 记录（它拒绝 AI 批准者、拒绝跳序）：

```powershell
.\.venv\Scripts\python.exe 90_工具与配置\scripts\gate_control.py approve G1 `
  --approved-by "team-lead" --note "数据支持这条路线" --selected-problem "..."
```

工作模式决定每个 Gate 的仪式量，但**任何模式都不会削弱 G7，也不会允许自动批准**。
注意：`modes --mode X` 只是**查看**某个模式的配置，不会切换；切换要用 `modes set`：

```powershell
.\run.ps1 modes                          # 查看当前模式与各 Gate 的档次
.\run.ps1 modes --mode competition       # 只查看 competition 的配置，不切换
.\run.ps1 modes set competition          # 真正切换到 competition
.\run.ps1 modes set research             # 切回默认
```

- `research`（默认，向后兼容）：G1–G7 全部 `required`，完整批准记录 + 产物快照。
- `competition`：G1/G2/G3/G5/G7 仍为 `required`（G7 永远不弱化），G4 与 G6 降为
  `confirm`——仍然需要具名的**人**和说明，只是不再要求产物快照；未能绑定的依赖会写进
  该 Gate 记录的 `unbound_dependencies`，不会静默略过。

切换模式只改变后续 Gate 需要多少仪式量：不重写任何已有批准记录（更严格模式下记录的
批准在更轻模式下依然有效，因为它要求的证据是超集）。模式配置损坏时会回落到最严格的
`research`，绝不会"失败即放行"。当前模式存放在受版本管理的
`90_工具与配置/configs/workflow-mode.txt`，所以团队能在仓库里看到正在用哪种模式；
删掉该文件即回落到 `workflow-modes.yaml` 的 `default_mode`。

模式是**项目配置，不是本地状态**：`modes set` 只写这一个文件，**不会自动 commit，也不会
批准或撤销任何 Gate**。建议在正式运行前把这次模式切换 commit 下来，让一次完整工作所用
的模式可以追溯；当前模式也会出现在 `run.ps1 gates` 与 `run.ps1 info` 的输出里。

### 记录独立最终验证

`90_工具与配置/reports/verify.json` 必须由独立复核人具名完成。这是一个窄接口，只负责
校验并记录**人的结论**；它不会读取机器 `verify` 的结果、也不会替你把确定性检查升级为
独立验证，更不会批准 G7：

```powershell
.\run.ps1 final-review show                # 当前记录与 G7 前置条件
.\run.ps1 final-review record `
  --reviewer "Prof. Li" `
  --note "独立复核了结果表、图与主张链" `
  --check "pass:deterministic_chain:ran verify --with-tests" `
  --check "pass:figure_hashes"
.\run.ps1 final-review reset               # 回到 pending
```

约束是硬性的：`--reviewer` 不能是 AI/自动化身份，`--note` 与至少一条 `--check` 必填，
存在非 `pass` 的 check 时不允许记为 `verified`（要用 `--reject`）。

## 命令一览

| 命令 | 作用 |
| --- | --- |
| `run.ps1 setup` | 建立/刷新 `.venv` 并安装依赖（幂等） |
| `run.ps1 doctor` | 检查解释器、依赖与外部工具 |
| `run.ps1 status` | 项目状态、阶段、Gate 与产物计数 |
| `run.ps1 validate` | 结构检查 + 契约校验 |
| `run.ps1 test` | 运行 pytest 测试套件 |
| `run.ps1 lint` | 按仓库配置运行 ruff（`--fix` / `--format`） |
| `run.ps1 verify` | 确定性验证全链路（结构/契约/Gate/失效/主张/AI 溯源/合规/打包边界） |
| `run.ps1 package` | 通过完整守卫链检查或构建提交包 |
| `run.ps1 clean` | 清理可再生的缓存（绝不删除 tracked 文件） |
| `run.ps1 demo` | 运行或复核最小端到端 Demo |
| `run.ps1 modes` | 查看/切换 research 与 competition 工作模式（`modes set <mode>`） |
| `run.ps1 final-review` | 记录/查看独立最终验证结论（`show` / `record` / `reset`） |
| `run.ps1 plan` | 把复杂请求拆成带依赖的 task DAG |
| `run.ps1 route` | 单个请求的确定性路由预览 |
| `run.ps1 gates` | 只读查看 G1–G7 状态 |
| `run.ps1 skills` | 列出项目 Skills |
| `run.ps1 agents` | 列出项目 Agents |
| `run.ps1 hash` | 计算官方输入哈希（`--update` 写回 manifest） |
| `run.ps1 compliance` | 规则驱动的合规检查 |
| `run.ps1 info` | 解析后的仓库路径与解释器 |
| `run.ps1 git-status` | 本仓库的简短 git 状态 |

`verify` 与 `package` 的边界（重要）：

- `verify` 执行真实检查并如实报告，其中「比赛尚未配置、尚无主张、尚无 Gate 批准」这类
  未开工项标为 `later`，不会被伪装成通过。它**不会**把
  `90_工具与配置/reports/verify.json` 写成 `verified`——独立验证必须由独立复核人具名记录。
- `package` 在 G7 未批准、独立验证未完成或边界规则不通过时**正确地 BLOCKED 并非零退出**，
  不会创建任何压缩包，也不会绕过 compliance、verify 或 package guard。

### 运行前置未就绪时

除 `setup` 之外的任何 `run.ps1` 命令在 `.venv` 缺失时都会明确告诉你下一步：

```text
Project Python is missing.
  expected: <repo>\.venv\Scripts\python.exe

Run the setup step first:
  PowerShell :  .\run.ps1 setup
  or         :  .\setup.ps1
  cmd.exe    :  run.ps1 setup
  Git Bash   :  ./setup.sh
```

## Skills 与 Agents 概览

22 个项目 Skills，覆盖证据检索、文献核验、问题分析、数据审计、路线比较、数学推导、
MODEL_SPEC、求解策略、实现、优化、验证/UQ、复现、科学制图、论文、合规与上下文治理。

11 个专职 Agents 分两类，读写边界是这个系统的核心安全边界：

- **只读复核者（不写任何产物）**：`researcher`、`critic`、`judge`、`validator`、
  `replicator`、`reviewer`、`compliance`。它们只返回证据与判断，由父调度器汇总。
- **写入者（同一产物只有一个）**：`deriver`（写模型推导）、`implementer`（写基线与代码）、
  `optimizer`（写实验与优化运行）、`visualizer`（写正式图与渲染代码）。

只读复核可以并行；写同一产物时其余 writer 必须等待。`researcher`、`critic`、`judge`
之所以是只读，是为了让"调查"和"独立评判"不能被写成既成事实。

完整的 22 个 Skill 与 11 个 Agent 功能表见
[CODEX_CAPABILITIES.md](CODEX_CAPABILITIES.md)；日常操作细节见
[数学建模工作区使用说明.md](数学建模工作区使用说明.md)。

## 目录

```text
01_题目与要求/       官方题目、附件、规则（只读源）
02_参考文献/         用户提供或核验后的参考资料
03_建模工作区/       问题分析、模型、代码、测试、实验、结果、图表、运行记录
04_论文与提交/       论文、引用、AI 使用记录和提交包
90_工具与配置/       Agent、Skill、路由、脚本、Schema、模板与工具报告
examples/toy_demo/   最小端到端示例（合成数据）
.github/workflows/   CI（ruff / 结构契约 / verify / pytest）
.agents/ .codex/     客户端发现镜像
```

正式代码只进 `03_建模工作区/src/`，正式论文只进 `04_论文与提交/paper/`。
根目录 `.agents` 与 `.codex` 是发现入口，权威副本在 `90_工具与配置/` 下。

## 开发与测试

```powershell
.\setup.ps1 -Ci -NoDoctor
.\run.ps1 lint
.\run.ps1 test
.\run.ps1 verify
.\run.ps1 validate
```

CI（`.github/workflows/ci.yml`）在 push 与 pull_request 上运行，矩阵为
Ubuntu/Windows × Python 3.11/3.13，步骤依次是 setup → ruff → CLI help → doctor →
validate → verify → pytest。CI 不需要任何密钥、赛题数据，也不要求人工 Gate 已批准；
提交前的最终验证与普通代码 CI 是分开的两件事。

`ruff` 配置见 `pyproject.toml`。E501（行长）在 `[tool.ruff.lint.per-file-ignores]` 中被
显式忽略并注明原因：本仓库脚本与测试历史上按 100 列以上书写，全仓重排不在本次修改范围内；
F/I/UP/B 这些能抓到真实 bug 与不稳定写法的规则保持全量启用。

## 高级架构

- `90_工具与配置/scripts/`：确定性工具层（状态、契约、运行记录、主张、Gate、打包守卫）。
- `90_工具与配置/schemas/`：11 个机器可校验结构。
- `90_工具与配置/configs/`：`auto-routing.yaml`（权威路由表）、`workflow-modes.yaml`
  （工作模式）、`artifact_boundaries.yaml`（打包边界）、`contest.yaml`（赛制规则）等。
- `90_工具与配置/templates/`：Figure Contract 与 LaTeX 模板。
- `90_工具与配置/reports/verify.json`：独立最终验证记录，默认 `pending`，只能由独立复核人完成。
- `90_工具与配置/reports/verify-run.json`：`verify` 自身的机器可读运行报告（可选 `--write-report`）。

## 安全与复现原则

- 不编造命令输出、数据、文献、实验、图表或通过状态。
- 不把 solver success 当成模型正确；推导、实现与验证分别审查。
- 不在公开模板中保存密钥、私有仓库地址、个人绝对路径或具体赛题成果。
- Agent、Skill、测试与 Hook 只能报告准备度，不能批准 Gate。
- 范文只用于学习结构与深度，引用和复用必须遵守来源许可及竞赛规则。

## 来源与许可

- 本仓库的代码与文档采用 **[MIT License](LICENSE)**（Copyright (c) 2026 haohan-sun）。
- 第三方组件仍受各自许可证约束，根许可证不改变它们的权利状态：逐项目清单与
  例外（含 CC-BY-4.0 的历史制图参考）见 [NOTICE](NOTICE)。请勿把第三方代码
  重新声明为 MIT，也不要删除其中的原始版权声明。
- 第三方设计参考与许可证记录见
  [90_工具与配置/third_party/UPSTREAM_SOURCES.md](90_工具与配置/third_party/UPSTREAM_SOURCES.md)；
  `mm-mathematical-derivation` 的方法来源见其
  `references/methodology-sources.md`。
- `context-optimization` Skill 来源于宽松许可的上游项目，来源与提交哈希记录在
  [CODEX_CAPABILITIES.md](CODEX_CAPABILITIES.md)。
