# 竞赛代码风格规范

适用于 `03_建模工作区/src/`、`tests/`、`experiments/` 全部 Python 代码。
目标：评审可读、队友可接手、结果可复现。

## 通用规则

1. **格式**：PEP 8；行宽 100；所有模块 `from __future__ import annotations` 开头。
   类型注解用于函数签名，函数体内部不必逐变量注解。
2. **命名**：变量/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_CASE`。
   禁止 `df2`、`tmp3` 这类无信息命名；用 `demand_matrix`、`route_plan`。
3. **注释密度**：与周围代码一致。注释说明"为什么/约束"，不复述代码。
   公共函数写 docstring：一句话用途 + 参数/返回（NumPy 风格可省略参数表，但
   数值算法必须说明单位与量纲）。
4. **单一路径**：正式代码只写 `src/`；一次性探索脚本放 `experiments/scratch/`
   并在提交前删除。禁止笔记本（.ipynb）进入正式流程。

## 科学计算约定

5. **随机性可复现**：所有随机过程用 `np.random.default_rng(seed)`，
   seed 为命名常量（`SEED = 42`）写在模块顶部；多种子实验由调用方传入。
6. **无魔数**：物理/经济常数、迭代参数必须命名常量或配置项，附来源注释
   （题目给定 / 文献值 / 拟合结果）。
7. **数据边界**：读数据用相对工作区根的路径或 `pathlib`；禁止绝对盘符路径
   写死在正式代码里。输入数据不改写；所有派生结果写 `results/` 并带时间戳
   或 result_id。
8. **数值稳健**：除法前检查分母；优化求解后检查 `status`/`success`；
   禁止吞异常——失败要带着错误信息停下来。
9. **依赖收敛**：新依赖先加进 `pyproject.toml` 并在论文"模型求解"节说明；
   优先 numpy/scipy/pandas/sklearn/statsmodels，图形一律 matplotlib
   （经 `src/viz/style_presets.py`），不混用多个绘图后端。

## 绘图约定（最重要的门面）

本节仅为实现说明；唯一视觉规范为 `configs/VISUAL_STYLE_GUIDE.md`，冲突时以该文件为准。

10. 样式只能来自 `src/viz/style_presets.py`（`apply_style`），禁止在绘图代码
    里散落 `rcParams` 或逐条 `set_color`。
11. 每图必有：坐标轴含义与单位、图例、可追溯的文件名
    （`figN_内容描述.png/pdf`）。保存统一走 `save_figure`。
12. 正式图的数据只能来自 `results/` 注册结果；探索图不进 `figures/`。

## 测试与验收

13. 每个正式模块至少一个冒烟测试（合成数据、快速阈值断言），放 `tests/`，
    能用 `python -m tests.<name>` 直接运行。
14. 提交前跑 `./run.ps1` 的状态/校验入口，绿了才算完成。
