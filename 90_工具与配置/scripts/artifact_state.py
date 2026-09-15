"""Artifact snapshots: dependency-based Gate invalidation.

At a Gate PASS, snapshot the SHA-256 of artifacts the Gate depends on. Later,
`invalidate()` detects any substantive modification and reports the affected
Gates. A stale Gate must be re-approved by a human — scripts only report.

State file: 90_工具与配置/state/artifact_snapshots.json

CLI:
    python .../artifact_state.py --snapshot G5 path1 path2 ...
    python .../artifact_state.py --check        # list invalidated gates
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, sha256_file

STATE_PATH = ROOT / "90_工具与配置" / "state" / "artifact_snapshots.json"
# Dependency map: a Gate's approval is only valid while these artifacts stay unchanged.
GATE_DEPENDENCIES: dict[str, list[str]] = {
    "G1": ["01_题目与要求", "03_建模工作区/decisions/DECISION_LOG.md"],
    "G2": ["03_建模工作区/decisions/route-tree.json",
           "03_建模工作区/problem/PROBLEM_ANALYSIS.json",
           "03_建模工作区/model/HUMAN_MODEL_IDEAS.md",
           "03_建模工作区/decisions/DECISION_LOG.md"],
    "G3": ["03_建模工作区/model/MODEL_SPEC.md"],
    "G4": ["03_建模工作区/model/MODEL_SPEC.md", "03_建模工作区/src"],
    "G5": ["03_建模工作区/model/MODEL_SPEC.md", "03_建模工作区/src", "03_建模工作区/results"],
    "G6": ["03_建模工作区/figures/manifest.json", "03_建模工作区/figures/final"],
    "G7": ["04_论文与提交/paper",
           "04_论文与提交/references",
           "04_论文与提交/ai_provenance/AI_USAGE_SUBMISSION.md",
           "90_工具与配置/configs/contest.yaml",
           "90_工具与配置/reports/verify.json"],
}
GATE_PARENTS = {"G2": ["G1"], "G3": ["G2"], "G4": ["G3"], "G5": ["G4"],
                "G6": ["G5"], "G7": ["G6"]}


def resolve_artifact(dep: str, root: Path = ROOT) -> Path:
    """Reject traversal and links escaping the project, including nested links."""
    root = root.resolve()
    target = (root / dep).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"artifact outside project: {dep}")
    if target.is_dir():
        for item in target.rglob("*"):
            if not item.resolve().is_relative_to(root):
                raise ValueError(f"artifact link outside project: {item}")
    return target


def _load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": "1.0", "snapshots": {}}


def _save_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hash_target(target: Path) -> str:
    """File -> its hash; directory -> hash of (relative name, hash) pairs."""
    if target.is_file():
        return sha256_file(target)
    if target.is_dir():
        import hashlib

        digest = hashlib.sha256()
        for file in sorted(target.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                digest.update(file.relative_to(target).as_posix().encode())
                digest.update(sha256_file(file).encode())
        return digest.hexdigest()
    return "MISSING"


def snapshot(gate: str, extra_paths: list[str] | None = None, *, path: Path = STATE_PATH,
             root: Path = ROOT, human_approval: str | None = None) -> dict[str, str]:
    gate = gate.upper()
    if gate not in GATE_DEPENDENCIES:
        raise ValueError(f"unsupported gate: {gate}")
    state = _load_state(path)
    # Baseline capture is not approval. Replacing one requires an external human record.
    if gate in state["snapshots"] and not human_approval:
        raise ValueError("replacing a snapshot requires a human approval record")
    deps = GATE_DEPENDENCIES.get(gate.upper(), []) + list(extra_paths or [])
    hashes = {}
    for dep in deps:
        target = resolve_artifact(dep, root)
        hashes[dep] = _hash_target(target)
    state["snapshots"][gate.upper()] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hashes": hashes,
        "human_approval": human_approval,
    }
    _save_state(state, path)
    return hashes


def invalidate(path: Path = STATE_PATH, *, root: Path = ROOT) -> list[str]:
    """Return gates whose dependent artifacts changed after their snapshot."""
    state = _load_state(path)
    stale: list[str] = []
    for gate, snap in state["snapshots"].items():
        for dep, old_hash in snap["hashes"].items():
            current = _hash_target(resolve_artifact(dep, root))
            if current != old_hash:
                stale.append(f"{gate}: {dep} changed after PASS ({old_hash[:8]} -> {current[:8]})")
                break
    invalid = {message.split(":", 1)[0] for message in stale}
    for gate, parents in GATE_PARENTS.items():
        if gate not in invalid and any(parent in invalid for parent in parents):
            stale.append(f"{gate}: upstream PASS invalidated")
            invalid.add(gate)
    return stale


def invalidate_manifest(manifest: dict[str, Any], *, path: Path = STATE_PATH,
                        root: Path = ROOT) -> list[str]:
    """In-memory only: downgrade approvals; never create or approve a Gate."""
    reasons = invalidate(path, root=root)
    gates = manifest.get("gates", {})
    entries = list(gates.items()) if isinstance(gates, dict) else list(
        (g.get("id", g.get("gate_id")), g) for g in gates
    )
    entries.extend((stage.get("name", "").split(" ", 1)[0], stage)
                   for stage in manifest.get("stages", []))
    stale = {reason.split(":", 1)[0] for reason in reasons}
    for gate, entry in entries:
        if gate in stale and isinstance(entry, dict):
            if str(entry.get("status", "")).lower() in {"approved", "pass", "passed"}:
                entry["previous_status"] = entry["status"]
                entry["status"] = "pending"
                entry["invalidation_reason"] = next(r for r in reasons if r.startswith(gate + ":"))
    return reasons


def sync_manifest(manifest: dict[str, Any], *, path: Path = STATE_PATH,
                  root: Path = ROOT) -> list[str]:
    """Persist no approvals: capture new human records, then invalidate unchanged old PASSes."""
    state = _load_state(path)
    invalid_approvers = {"ai", "agent", "codex", "orchestrator", "hook", "skill", "subagent"}
    for stage in manifest.get("stages", []):
        gate = str(stage.get("name", "")).split(" ", 1)[0].upper()
        approver = str(stage.get("approved_by", "")).strip()
        approved_at = str(stage.get("approved_at", "")).strip()
        approval = f"{approver} at {approved_at}"
        previous = state.get("snapshots", {}).get(gate, {}).get("human_approval")
        if (gate in GATE_DEPENDENCIES and stage.get("status") == "approved"
                and approver and approver.casefold() not in invalid_approvers and approved_at
                and previous != approval):
            snapshot(gate, path=path, root=root,
                     human_approval=approval)
            state = _load_state(path)
    reasons = invalidate_manifest(manifest, path=path, root=root)
    if reasons:
        manifest["stale_artifacts"] = sorted(set(manifest.get("stale_artifacts", [])) | set(reasons))
    return reasons


def recover(gate: str, *, path: Path = STATE_PATH, human_approval: str | None = None,
            root: Path = ROOT) -> dict[str, str]:
    """Re-snapshot after human re-approval; call only from an approval flow."""
    if not human_approval:
        raise ValueError("human approval record required")
    return snapshot(gate, path=path, human_approval=human_approval, root=root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate artifact snapshots.")
    parser.add_argument("--snapshot", metavar="GATE")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--recover", metavar="GATE")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.snapshot:
        print(json.dumps(snapshot(args.snapshot, args.paths), ensure_ascii=False, indent=2))
        return 0
    if args.recover:
        print(json.dumps(recover(args.recover), ensure_ascii=False, indent=2))
        return 0
    stale = invalidate()
    print("\n".join(stale) if stale else "artifact snapshots: all gates valid")
    return 0 if not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
