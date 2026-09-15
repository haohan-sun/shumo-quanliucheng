"""Problem analysis artifact validator (schemas/problem-analysis.schema.json).

jsonschema-free structural check: required keys, enum membership, reference
integrity (subproblem ids, dependency closure), and completeness ratios.

CLI:
    python .../problem_analysis.py --check 03_建模工作区/problem/PROBLEM_ANALYSIS.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TASK_TYPES = {"decision", "prediction", "optimization", "simulation", "inference",
              "evaluation", "allocation", "scheduling", "network", "control"}
REQUIRED = ("schema_version", "problem_id", "subproblems", "task_types", "variables",
            "objectives", "constraints", "assumption_ledger", "data_requirements",
            "output_requirements", "evaluation_metrics", "identifiability_risks",
            "hidden_requirements", "terminology")


def check_analysis(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(artifact, dict):
        return ["artifact must be an object"]
    for key in REQUIRED:
        if key not in artifact:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors
    if artifact["schema_version"] != "1.0":
        errors.append("schema_version must be '1.0'")
    bad_types = [t for t in artifact["task_types"] if t not in TASK_TYPES]
    if bad_types:
        errors.append(f"unknown task_types: {bad_types}")

    raw_sub_ids = [sub.get("id") for sub in artifact["subproblems"]]
    sub_ids = set(raw_sub_ids)
    if len(raw_sub_ids) != len(sub_ids):
        errors.append("subproblem ids must be unique")
    if None in sub_ids or "" in sub_ids:
        errors.append("every subproblem needs a non-empty id")
    for sub in artifact["subproblems"]:
        dangling = [d for d in sub.get("depends_on", []) if d not in sub_ids]
        if dangling:
            errors.append(f"subproblem {sub.get('id')}: unknown dependency {dangling}")
    # dependency closure: no cycles (DFS)
    state: dict[str, int] = {}

    def visit(sid: str) -> bool:
        if state.get(sid) == 1:
            return True
        if state.get(sid) == 2:
            return False
        state[sid] = 1
        sub = next((s for s in artifact["subproblems"] if s["id"] == sid), None)
        if sub:
            if any(visit(d) for d in sub.get("depends_on", [])):
                return True
        state[sid] = 2
        return False

    if any(visit(sid) for sid in sub_ids):
        errors.append("subproblem dependency graph contains a cycle")

    for obj in artifact["objectives"]:
        if obj.get("sense") not in {"minimize", "maximize"}:
            errors.append(f"objective {obj.get('id')}: sense must be minimize/maximize")
    for con in artifact["constraints"]:
        if con.get("source") not in {"problem", "derived", "assumption"}:
            errors.append(f"constraint {con.get('id')}: unknown source")
    for assumption in artifact["assumption_ledger"]:
        if assumption.get("strength") not in {"weak", "moderate", "strong"}:
            errors.append(f"assumption {assumption.get('id')}: unknown strength")
    for risk in artifact["identifiability_risks"]:
        if risk.get("severity") not in {"low", "medium", "high"}:
            errors.append("identifiability risk: unknown severity")

    vars_ = artifact.get("variables", {})
    for role in ("decision", "state", "exogenous"):
        for var in vars_.get(role, []):
            if not var.get("name") or "unit" not in var:
                errors.append(f"{role} variable {var.get('name')!r}: needs name and unit")
    if not artifact["objectives"]:
        errors.append("at least one objective is required")
    if not artifact["evaluation_metrics"]:
        errors.append("at least one evaluation metric is required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a problem analysis artifact.")
    parser.add_argument("--check", type=Path, required=True)
    args = parser.parse_args()
    artifact = json.loads(args.check.read_text(encoding="utf-8"))
    errors = check_analysis(artifact)
    print("\n".join(errors) if errors else "problem analysis: PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
