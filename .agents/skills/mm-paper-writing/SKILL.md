---
name: mm-paper-writing
description: "AUTO TRIGGER: a request is to WRITE, draft, translate into polished prose, restructure, or polish competition paper sections (abstract, problem restatement, assumptions, notation, model building, solution, sensitivity, strengths/weaknesses) from registered results. DO NOT TRIGGER: paper consistency audit (mm-paper-defense), citation identity checks (mm-literature-integrity), result validity audit (mm-result-audit), figure rendering (mm-scientific-visualization), or submission packaging (mm-compliance). STAGE: S12 drafting after G5. INPUTS: MODEL_SPEC, registered results, figure manifest, competition format spec. OUTPUTS: paper sections in 04_论文与提交/paper/ with claim-to-result traceability. BOUNDARIES: writes prose only from verified results; never invents numbers, citations, or figure references; never approves G5/G6/G7."
---

# MM Paper Writing

从已注册的真实结果撰写竞赛论文。只允许写经过验证的内容：每个数字、每个图表引用
必须能追溯到 `03_建模工作区/results/` 与 figure manifest 的记录。论文写入
`04_论文与提交/paper/`。

## 工作流

1. **盘点素材**：读取 MODEL_SPEC、结果文件、figure manifest、赛题格式规范。
   缺素材（如某灵敏度结果未跑）时先列缺口清单，不得编造占位数字。
   每个数值主张在 claim registry 中绑定 run_id、metric 与当前输出哈希；调用
   `90_工具与配置/scripts/claim_registry.py` 检查其可追溯性。run record 缺失、
   PASS 已失效或输出哈希变化时不得写成已验证结论。
2. **先写摘要**：摘要按"问题-方法-结果-亮点"四段式，每句话含具体数值结论。
   参考 `references/section_playbook.md` 的逐节指南与句式库。
3. **正文骨架**：按 `references/section_playbook.md` 的标准结构产出各节；
   每节写作前确认对应结果文件存在且非空。
4. **图表引用自检**：正文中每个 图X/表X 必须与 manifest 记录一一对应；
   未引用的图表要么补引用要么从论文移除。
5. **一致性交接**：写完后调用审查方（mm-paper-defense）做交叉审计；
   本技能不做最终审计结论。

## 红线

- 不得虚构数据、引用、图表或"我们验证了X"这类无对应结果的声明。
- 不得承诺创新性评价结论——那是评审与 G-gate 的事。
- 语言：中文论文用规范学术中文，英文论文用简洁学术英语；禁止口语与营销语气。

渐进式阅读：先读本文件即可动笔；逐节指南与句式库在 `references/`，
写作对应章节时再读。
