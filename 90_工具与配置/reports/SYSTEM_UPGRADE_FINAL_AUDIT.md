# 数学建模 Skill 系统升级最终审计

- 日期：2026-09-05
- 基线：`909a94f`
- 审计前实现 HEAD：`465a64b2b40a74df13d16b259c6a4e56e8722bba`
- 结论：PASS（有一项宿主发现时机限制，见“尚存风险”）

## Zcode 已完成的基础

Zcode 已建立五项新增能力的 Skill/脚本/schema 初稿、有限方案树初稿、
validator/replicator 初稿、artifact/run/claim/package 辅助脚本及架构调研。
这些内容保留并增量修复，没有推倒重写。

## 本轮补完与修复

1. route tournament：补全有限节点/深度/quick-test/beam 预算、状态机、CLI、
   人工 G2 绑定；G2 现在同时绑定 problem、route 和 route-tree 内容哈希。
2. 自动路由：五项新能力与 mm-paper-writing 均进入 auto-routing；补 judge，
   validator/replicator/judge 全为 read-only；自然语言“候选建模路线/方案树/beam”可命中。
3. 视觉：`configs/VISUAL_STYLE_GUIDE.md` 是唯一规范源，旧画图文档为 legacy，
   CODE_STYLE 与 viz README 仅作实现说明。
4. 打包：build_submission 在创建 zip 前强制 package guard；拒绝所有层级 locked cache、
   内部状态、绝对/穿越路径和链接，不能从 library API 绕过 G7。
5. PASS 失效：G1-G7 均有内容哈希依赖并传递失效；旧批准不能覆盖新 artifact；
   新人工批准记录可重新快照，Hook SessionStart/Stop 接入同步。
6. 证据链：输入、代码、配置、seed、依赖、输出哈希进入 run manifest；
   result/comparison/robustness/answer 主张必须绑定可校验 run，URL 不能替代计算证据。
7. 数据审计语法错误、缺列/概率边界、输出位置和 JSON schema 契约已修复；
   pytest 临时目录按进程隔离，支持多个只读验证并行。
8. 新增最小 workflow benchmark，覆盖 7 类自然语言路由、3 个只读角色配置和 package guard。

## 实测

- Python compileall：PASS
- JSON / YAML / TOML parse：PASS
- structure：PASS
- contracts：PASS
- pytest：62 passed（5.55s）
- 可视化模板：7/7 passed
- SessionStart Hook：PASS，G1-G7 均保持 pending，未自动批准
- benchmark：PASS，100 iterations / 700 routing operations，8.3792s，83.54 ops/s，0 mismatch
- 独立 verifier：57 passed（修复前）并定位方案树自然语言缺口；修复后全量 62 passed
- 独立 reviewer：定位 G2 hash、G1/G2 失效链、URL 绕过 run 三处高风险；均已修复并回归通过

## 尚存风险

当前会话的 subagent API 只暴露内建角色枚举，不暴露项目自定义
validator/replicator/judge 作为可点名类型，因此本轮能真实验证其 TOML、只读权限、
自然语言调度输出和独立 reviewer/verifier 交接，但不能在同一会话中完成三个新角色的
宿主级点名 spawn。新任务/工作区启动时 Codex 会重新发现 `.codex/agents/*.toml`；
若客户端版本不支持项目自定义角色，需要升级客户端，配置本身不会降级为写权限。

## Checkpoint commits

- `f9c0d20` bounded route tournament
- `f8e7af4` specialist agents and routing
- `50d5f2b` package guard and visual policy
- `d96b7b1` invalidation and provenance
- `c01ec4c` modeling analysis capabilities
- `5158796` evals and runtime smoke
- `465a64b` gate/evidence-chain review fixes

基线差异（审计前）：72 files changed, 3687 insertions, 73 deletions。
