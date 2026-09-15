# Codex Agent / Skill 清单

更新日期：2026-09-16

## Agents（11）

- compliance
- critic
- deriver
- implementer
- judge
- optimizer
- replicator
- researcher
- reviewer
- validator
- visualizer

项目配置真源为 `90_工具与配置/.codex/agents/`，根目录 `.codex/agents/` 是公开模板的
发现镜像；发布检查要求两处一致。

## Skills（22）

- context-optimization
- mm-ai-provenance
- mm-compliance
- mm-cumcm-paper-writing-review
- mm-data-audit
- mm-evidence-retrieval
- mm-experiment-optimization
- mm-implementation
- mm-literature-integrity
- mm-mathematical-derivation
- mm-model-spec
- mm-orchestrator
- mm-paper-defense
- mm-paper-writing
- mm-preflight
- mm-problem-analysis
- mm-reproducibility
- mm-result-audit
- mm-route-tournament
- mm-scientific-visualization
- mm-solver-strategy
- mm-validation-uq

项目配置真源为 `90_工具与配置/.agents/skills/`，根目录 `.agents/skills/` 是发现镜像。
`mm-cumcm-paper-writing-review` 由仓库所有者原创提供，并已移除本机路径；
`mm-mathematical-derivation` 依据公开方法资料原创整理，不复制第三方代码或文本。

## 保留的环境与模板

- 环境定义：`pyproject.toml`、`uv.lock`
- 工作流入口：`AGENTS.md`、`run-manifest.json`、`run.ps1`
- 路由、脚本、Schema：`90_工具与配置/configs/`、`scripts/`、`schemas/`
- 论文与图形模板：`90_工具与配置/templates/`

缓存、虚拟环境、临时运行目录、竞赛数据和重复封包均不属于公开模板真源。
