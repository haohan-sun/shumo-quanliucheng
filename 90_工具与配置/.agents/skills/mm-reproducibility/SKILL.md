---
name: mm-reproducibility
description: "AUTO TRIGGER: any important experiment, baseline, validation, or figure-generating run must be wrapped in a run record (run_id, git state, input hashes, config, seeds, deps, command, outputs, metrics, parent run, model spec version); also for replication checks and for tracing paper numbers to run_ids. DO NOT TRIGGER: casual exploration scripts under experiments/scratch, doc edits, or visualization-only preview. STAGE: cross-stage S7-S13. INPUTS: command, config, seeds, output paths. OUTPUTS: 03_建模工作区/runs/<run_id>/manifest.json + registry.csv. BOUNDARIES: bookkeeping only; never certify a run it did not record, never approve Gates."
---

# MM Reproducibility

每个重要实验 = 一个 run 目录 + 一份 manifest + 一条最小复现命令。
论文里的关键数字必须能给出 run_id。

## 正式计算（推荐且可进入论文）

所有准备进入结果表、图或论文的计算，统一通过包装器真实执行；包装器会在启动前建档，
并在成功、失败或超时后保存标准输出、错误输出、退出码、运行时长和声明产物哈希：

```powershell
.\.venv\Scripts\python.exe 90_工具与配置/scripts/tracked_run.py `
  --config '{"model":"baseline"}' --seed main=42 `
  --input 01_题目与要求 --code 03_建模工作区/src `
  --output metrics=03_建模工作区/results/metrics.json --timeout 600 -- `
  .\.venv\Scripts\python.exe 03_建模工作区/src/<your_script>.py
```

`<your_script>.py` 是本项目按 MODEL_SPEC 实现的计算入口（G4 基线就是第一个）。
没有实现脚本时，可先用公开的玩具算例 `examples/toy_demo/src/fit_decay.py` 走通整条链路。

`run_record.py` 的库接口仅用于需要程序内分阶段登记的高级场景；只创建/补写记录、
却没有成功退出码和真实产物的 bookkeeping record 不能支撑计算型论文 claim。

## 程序内高级用法

```python
import sys

sys.path.insert(0, "90_工具与配置")
from scripts.run_record import create_run, finalize_run, add_output

run = create_run(
    config={"model": "baseline", "lr": 0.1},
    seeds={"main": 42},
    command=["python", "03_建模工作区/src/<your_script>.py", "--lr", "0.1"],
)
# ... 执行并写入输出文件 ...
add_output(run, "results/metrics.json", kind="metrics")
finalize_run(run, metrics={"rmse": 0.31}, runtime_seconds=12.4)
```

## 目录契约

`03_建模工作区/runs/<run_id>/`：
`manifest.json`（最终）、`config/resolved.json`、`figures/`、`tables/`、
`artifacts/`、可选 `stdout.log`/`stderr.log`；`registry.csv` 汇总索引。

## 必须落 run record 的场景

1. G4 基线及其验收比较；2. G5 之前的最终方法全套结果；
3. 验证/UQ 全部实验（mm-validation-uq）；4. 生成正式图的渲染运行；
5. 任何将被论文引用为数字的计算。

## 检查与恢复

- `python 90_工具与配置/scripts/run_record.py --list` 查看全部 run；
- manifest 含 git commit + dirty 标志：dirty 状态的 run 只能算初步结果；
- 复现检查（replicator 代理）：从 manifest 重建输入哈希与命令，
  在干净状态下重跑并比较 outputs 哈希/指标容差；
- 断点恢复：`parent_run` 链 + `config/resolved.json` 允许从任意节点分支续跑。

## 红线

- 无 run record 的数字不得进入论文 claim registry（claim_registry 会校验）。
- 事后改 config 不重跑 = 造假；必须新开 run。
