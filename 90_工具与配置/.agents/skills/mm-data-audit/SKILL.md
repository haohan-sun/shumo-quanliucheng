---
name: mm-data-audit
description: "AUTO TRIGGER: before formal modeling, when attachments or datasets must be screened for schema, dtype, missing, duplicate, outlier, unit, encoding, temporal order, geographic consistency, sampling bias, leakage, label leakage, impossible values, distribution shift, or sample sufficiency. DO NOT TRIGGER: problem decomposition (mm-problem-analysis), literature citation checks, modeling route selection, or preprocessing implementation inside a G3-frozen model. STAGE: S2c after problem analysis and before route tournament / MODEL_SPEC. INPUTS: raw data files, problem analysis data_requirements. OUTPUTS: data dictionary, audit report (data-audit.schema.json), preprocessing contract, rejected assumptions, unresolved risks. BOUNDARIES: screening and contracts only; never silently impute or drop rows, never edit raw data."
---

# MM Data Audit

正式建模前对全部输入数据做质量审计。产出写入
`03_建模工作区/data/audits/<dataset>.audit.json`，其结论必须被
mm-model-spec 与 mm-implementation 引用（预处理的每一决定写进 preprocessing_contract）。

## 流程

1. **机器审计**：对每个数据文件运行
   `python 90_工具与配置/scripts/data_audit.py --input <file> --target <y> --time <t> --lat .. --lon ..`。
   覆盖 16 类检查（schema/dtype/missing/duplicate/outlier/unit/encoding/temporal/
   geographic/bias/leakage/label-leakage/impossible/shift/sufficiency）。
2. **人工判读**：机器只报模式，人工判断业务含义——outlier 是错误还是真实现象？
   sampling bias 是否来自题目采集方式？leakage 判定要检查数据生成时序，不只看列名。
3. **preprocessing contract**：每一步预处理 = 操作 + 理由 + reversible + 是否影响 target；
   训练前拟合的变换（标准化、PCA）必须声明"仅用训练折拟合"。
4. **rejected assumptions / unresolved risks**：被数据否定的直觉、无法解决的疑虑显式记录。
5. **verdict**：usable / usable_with_fixes / blocked。blocking finding 未解决时
   禁止进入 route tournament 收尾与 G3。

## 红线

- 不改原始数据；清洗产物写到 `data/processed/` 并可由 contract 逐步复现。
- 缺失值处理、异常剔除、单位换算没有写入 contract = 违规。
- verdict=blocked 的数据集被继续使用 = 违规，必须上报 orchestrator 与人工。
