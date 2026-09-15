from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, validate_layout

REQUIRED_DIRECTORIES = [
    ".codex/agents",
    ".agents/skills",
    "01_题目与要求",
    "02_参考文献",
    "03_建模工作区/data/raw",
    "03_建模工作区/data/processed",
    "03_建模工作区/decisions/MODEL_CHANGE_REQUESTS",
    "03_建模工作区/evidence",
    "03_建模工作区/experiments",
    "03_建模工作区/figures",
    "03_建模工作区/literature",
    "03_建模工作区/model",
    "03_建模工作区/problem",
    "03_建模工作区/results",
    "03_建模工作区/src",
    "03_建模工作区/tests",
    "04_论文与提交/ai_provenance",
    "04_论文与提交/paper",
    "04_论文与提交/references",
    "04_论文与提交/submission",
    "90_工具与配置/configs",
    "90_工具与配置/reports",
    "90_工具与配置/schemas",
    "90_工具与配置/scripts",
]
REQUIRED_FILES = [
    "AGENTS.md",
    "run-manifest.json",
    "pyproject.toml",
    "uv.lock",
    "90_工具与配置/configs/workspace-layout.yaml",
    "03_建模工作区/model/MODEL_SPEC.md",
    "03_建模工作区/model/HUMAN_MODEL_IDEAS.md",
    "03_建模工作区/evidence/EVIDENCE_PASSPORT.yaml",
    "03_建模工作区/experiments/registry.csv",
    "03_建模工作区/results/results.json",
    "03_建模工作区/figures/manifest.json",
    "04_论文与提交/references/references.json",
    "90_工具与配置/reports/verify.json",
    "04_论文与提交/ai_provenance/ledger.yaml",
]
ROLES = {
    "researcher": "read-only",
    "implementer": "workspace-write",
    "optimizer": "workspace-write",
    "visualizer": "workspace-write",
    "deriver": "workspace-write",
    "critic": "read-only",
    "reviewer": "read-only",
    "compliance": "read-only",
    "validator": "read-only",
    "replicator": "read-only",
    "judge": "read-only",
}
REQUIRED_SKILLS = {
    "mm-orchestrator",
    "mm-evidence-retrieval",
    "mm-route-tournament",
    "mm-model-spec",
    "mm-implementation",
    "mm-experiment-optimization",
    "mm-scientific-visualization",
    "mm-literature-integrity",
    "mm-result-audit",
    "mm-paper-defense",
    "mm-preflight",
    "mm-ai-provenance",
    "mm-compliance",
    "mm-data-audit",
    "mm-problem-analysis",
    "mm-solver-strategy",
    "mm-validation-uq",
    "mm-reproducibility",
    "mm-paper-writing",
    "mm-mathematical-derivation",
    "mm-cumcm-paper-writing-review",
}


def verify(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_layout(root))
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"missing directory: {relative}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")

    for role, expected_sandbox in ROLES.items():
        path = root / ".codex" / "agents" / f"{role}.toml"
        if not path.is_file():
            errors.append(f"missing agent config: {path.relative_to(root).as_posix()}")
            continue
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"invalid agent config {role}: {exc}")
            continue
        if config.get("name") != role:
            errors.append(f"agent name mismatch: {role}")
        if config.get("sandbox_mode") != expected_sandbox:
            errors.append(
                f"agent sandbox mismatch: {role} expected {expected_sandbox}, "
                f"got {config.get('sandbox_mode')}"
            )

    skills_root = root / ".agents" / "skills"
    for skill in sorted(REQUIRED_SKILLS):
        path = skills_root / skill / "SKILL.md"
        if not path.is_file():
            errors.append(f"missing skill: {skill}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or f"name: {skill}\n" not in text:
            errors.append(f"invalid skill front matter: {skill}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify required project structure and role policies."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = verify()
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print("structure: FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print("structure: PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
