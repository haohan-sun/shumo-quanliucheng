# Workflow Ready

## 已实现内容

- 建立 Python 3.12 项目虚拟环境，安装基础科学计算、统计、机器学习、绘图、Jupyter、PDF/Word 解析、验证与测试工具。
- 生成 `uv.lock`，锁定基础与全部可选组共 205 个可解析依赖；项目内缓存可用于离线锁文件复核。
- 建立人类 Gate、MODEL_SPEC 冻结、变更请求、证据、实验、结果、图表、引用、AI 使用和最终复核的真值源与 Schema。
- 建立结构、合同、输入哈希、状态、环境体检、AI 报告、合规、总验证和提交打包脚本。
- 提交脚本在赛事规则、控制号、论文 PDF、独立复核或合规条件缺失时拒绝打包。
- 未创建 Web UI，未开始真实赛题，未生成任何数据、引用、实验、结果或正式图表。

## 可用 Agent

- `researcher`：只读资料与证据研究。
- `critic`：只读候选路线反驳。
- `deriver`：把已选路线写成可审计数学推导，供 MODEL_SPEC 吸收。
- `reviewer`：只读独立结果与论文审查。
- `compliance`：只读赛事合规检查。
- `implementer`：按人类批准的 FROZEN MODEL_SPEC 实现。
- `optimizer`：对批准实现做求解、敏感性、鲁棒性和不确定性分析。
- `visualizer`：从真实数据或注册结果生成正式科研图。

## 可用 Skill

- `mm-orchestrator`
- `mm-preflight`
- `mm-evidence-retrieval`
- `mm-route-tournament`
- `mm-problem-analysis`
- `mm-data-audit`
- `mm-mathematical-derivation`
- `mm-model-spec`
- `mm-solver-strategy`
- `mm-implementation`
- `mm-experiment-optimization`
- `mm-validation-uq`
- `mm-reproducibility`
- `mm-scientific-visualization`
- `mm-literature-integrity`
- `mm-result-audit`
- `mm-paper-defense`
- `mm-paper-writing`
- `mm-cumcm-paper-writing-review`
- `mm-ai-provenance`
- `mm-compliance`

## 测试结果

本文件不保存可能过期的测试数字。公开发布前重新运行结构验证、Skill 快速校验、
自动路由测试、全量 pytest、敏感信息扫描和远端可见性检查，以实际命令输出为准。

## 缺失依赖

- Pandoc 未安装。
- LaTeX 工具链（`pdflatex`、`xelatex`、`latexmk`）未安装。
- `optimization`、`geospatial`、增强 `visualization` 可选组已锁定但未默认安装，应按真实赛题需要启用。

## 已知限制

- `contest` 仍为 `unassigned`，官方规则、控制号、页数和文件大小限制尚未录入。
- `MODEL_SPEC` 为 `UNINITIALIZED`；最终复核为 `pending`；项目不是 `READY_TO_SUBMIT`。
- 公开模板不含题目、附件、论文库、数据或赛题成果；使用者需自行放入并登记输入哈希。
- 比赛代码与实验只进入 `03_建模工作区/`，论文与提交物只进入 `04_论文与提交/`，Agent、Skill 和脚本只进入 `90_工具与配置/`。
- 数学推导 Skill 只非逐字吸收公开方法要点，来源与许可证记录在其 reference；后续复用任何第三方代码或文本仍需单独核验许可。

## 下一步怎么开始真实比赛题

1. 由队伍确认赛事与题目范围，并把官方规则录入 `90_工具与配置/configs/contest.yaml`。
2. 保持 `01_题目与要求/` 的官方源文件只读；清洗后的数据写入 `03_建模工作区/data/processed/`。
3. 运行 `.\run.ps1 hash -Update`，随后启动 S0 题目与附件体检。
4. 多题时只生成客观 `90_工具与配置/reports/PROBLEM_INVENTORY.md`，在 G1 等待队伍人工选题。
5. 队伍完成候选模型与最终 MODEL_SPEC；只有人类明确批准后才能进入 FROZEN、实现和实验阶段。
