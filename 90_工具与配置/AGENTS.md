# 工具区边界

继承根目录 `AGENTS.md` 的 AUTO-ORCHESTRATED MODE。任何非平凡基础设施任务也先由
`mm-orchestrator` 判断阶段和所有权；本目录只能有一个 writer。Hooks 只做确定性状态、
验证和 provenance 元数据工作，不得做科研判断或 Gate 审批。

本目录只拥有 Agent、Skill、脚本、配置、Schema、第三方方法说明和工具生成的检查报告。

项目根目录是 `..`。路径索引是 `configs/workspace-layout.yaml`。所有正式代码写入
`../03_建模工作区/src/`，所有论文与提交物写入 `../04_论文与提交/`；不得在本目录
生成比赛正文、模型结果或正式图表。

通常从根目录运行 `run.ps1`。根目录 `.agents` 与 `.codex` 提供 Codex 自动发现入口。
