"""Small deterministic benchmark for routing, guards and role wiring; no research work."""
from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT
from scripts.auto_route import route_task
from scripts.package_guard import excluded, load_boundaries

CASES = [
    ("问题拆解和假设账本", "mm-problem-analysis"),
    ("审计数据质量和缺失值", "mm-data-audit"),
    ("制定求解器策略", "mm-solver-strategy"),
    ("比较两个候选建模路线并做有限预算方案树", "mm-route-tournament"),
    ("模型验证和不确定性量化", "mm-validation-uq"),
    ("检查最小复现命令", "mm-reproducibility"),
    ("撰写论文摘要", "mm-paper-writing"),
]


def approved_manifest() -> dict:
    return {"stages": [{"name": f"G{i} gate", "status": "approved",
        "approved_by": "benchmark human fixture", "approved_at": "2026-09-05T12:00:00+08:00"}
        for i in range(1, 8)]}


def run_benchmark(iterations: int = 20, root: Path = ROOT) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    manifest = approved_manifest()
    started = time.perf_counter()
    misses = []
    for _ in range(iterations):
        for request, expected in CASES:
            actual = route_task(request, manifest, root=root).primary_skill
            if actual != expected:
                misses.append({"request": request, "expected": expected, "actual": actual})
    elapsed = time.perf_counter() - started
    roles = {}
    for name in ("validator", "replicator", "judge"):
        config = tomllib.loads((root / f"90_工具与配置/.codex/agents/{name}.toml").read_text(encoding="utf-8"))
        roles[name] = config.get("sandbox_mode") == "read-only"
    boundaries = load_boundaries(root / "90_工具与配置/configs/artifact_boundaries.yaml")
    guard = all(excluded(path, boundaries) for path in
                (".git/config", "src/_locked_cache_x/a", "../escape"))
    operations = iterations * len(CASES)
    return {"status": "PASS" if not misses and all(roles.values()) and guard else "FAIL",
            "iterations": iterations, "routing_operations": operations,
            "elapsed_seconds": round(elapsed, 6),
            "routing_ops_per_second": round(operations / elapsed, 2),
            "route_mismatches": misses, "read_only_roles": roles, "package_guard": guard}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_benchmark(args.iterations)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
