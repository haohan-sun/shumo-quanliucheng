"""Explicit Human Gate approval and revocation.

This module never decides whether a Gate should pass.  It only validates and
records an explicit human decision, binds the decision to current artifacts,
and asks :mod:`scripts.artifact_state` to capture their hashes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import dump_json, load_json
from scripts.artifact_state import GATE_DEPENDENCIES, recover, resolve_artifact, snapshot
from scripts.auto_route import EXPECTED_GATES, gate_inventory_errors, gate_records, valid_human_gate
from scripts.route_tree import load_tree, tree_fingerprint
from scripts.workflow_mode import (
    ModeError,
    current_mode,
    gate_requirement,
    requires_artifact_binding,
    requires_snapshot,
)

AI_IDENTITIES = {
    "ai", "agent", "codex", "chatgpt", "llm", "model", "orchestrator",
    "hook", "skill", "subagent", "bot", "assistant", "openai",
}


def _gate_id(value: str) -> str:
    gate = value.strip().upper()
    if gate not in EXPECTED_GATES:
        raise ValueError("gate must be one of G1-G7")
    return gate


def _human(value: str) -> str:
    value = value.strip()
    tokens = set(re.findall(r"[a-z0-9]+", value.casefold()))
    if not value or tokens & AI_IDENTITIES:
        raise PermissionError("approved_by/revoked_by must identify a human, not AI or automation")
    return value


def _note(value: str, label: str = "note") -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} is required")
    return value


def _root_for(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent


def _validated_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    errors = gate_inventory_errors(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    records = gate_records(manifest)
    gate_names = [re.match(r"^(G[1-7])\b", str(stage.get("name", "")), re.I)
                  for stage in manifest.get("stages", [])]
    ids = [match.group(1).upper() for match in gate_names if match]
    if len(records) != 7 or len(ids) != 7:
        raise ValueError("manifest must contain exactly one record for every G1-G7")
    if tuple(ids) != EXPECTED_GATES:
        raise ValueError("Human Gates must appear in G1-G7 order")
    schema_path = _root_for(manifest_path) / "90_工具与配置/schemas/run-manifest.schema.json"
    if schema_path.is_file():
        from jsonschema import Draft202012Validator, FormatChecker

        errors = list(Draft202012Validator(load_json(schema_path), format_checker=FormatChecker()).iter_errors(manifest))
        if errors:
            raise ValueError("manifest schema invalid: " + errors[0].message)
    return manifest


def _timestamp_after_prior(records: dict[str, dict[str, Any]], gate: str) -> str:
    now = datetime.now(timezone.utc)
    for previous in EXPECTED_GATES[: EXPECTED_GATES.index(gate)]:
        value = records[previous].get("approved_at")
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{previous} has invalid approved_at") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"{previous} approved_at must include a timezone")
        if parsed.astimezone(timezone.utc) > now:
            raise ValueError(f"{previous} approved_at is in the future")
    return now.isoformat(timespec="seconds")


def _stage_snapshot(stage: dict[str, Any]) -> dict[str, Any]:
    """Copy decision metadata without recursively embedding earlier history."""
    return {key: deepcopy(value) for key, value in stage.items() if key not in {"approval_history", "revocations"}}


def _replace_pair(manifest_path: Path, manifest: dict[str, Any], state_path: Path,
                  staged_state: Path) -> None:
    """Best-effort two-file transaction with rollback on replacement failure.

    ``staged_state`` may not exist: a Gate that only needs a human decision (the
    lightweight ``confirm`` tier) records nothing in the snapshot store, so the
    call is a plain manifest write. Rollback then just removes the state file it
    did not create.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=manifest_path.name + ".", suffix=".tmp",
                                           dir=manifest_path.parent)
    os.close(fd)
    staged_manifest = Path(temporary_name)
    staged_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    old_manifest = manifest_path.read_bytes()
    old_state = state_path.read_bytes() if state_path.exists() else None
    state_replaced = False
    try:
        if staged_state.exists():
            state_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_state, state_path)
            state_replaced = True
        os.replace(staged_manifest, manifest_path)
    except Exception:
        manifest_path.write_bytes(old_manifest)
        if state_replaced:
            if old_state is None:
                state_path.unlink(missing_ok=True)
            else:
                state_path.write_bytes(old_state)
        raise
    finally:
        staged_manifest.unlink(missing_ok=True)
        staged_state.unlink(missing_ok=True)


def approve_gate(
    manifest_path: Path,
    gate: str,
    *,
    approved_by: str,
    note: str,
    selected_problem: str | None = None,
    route_id: str | None = None,
    problem_id: str | None = None,
    route_tree_path: Path | None = None,
) -> dict[str, Any]:
    """Record an explicit approval; scientific readiness is never inferred here."""
    manifest_path = manifest_path.resolve()
    root = _root_for(manifest_path)
    gate = _gate_id(gate)
    approver = _human(approved_by)
    note = _note(note)
    manifest = _validated_manifest(manifest_path)
    records = gate_records(manifest)
    stage = records[gate]
    if valid_human_gate(manifest, gate):
        raise ValueError(f"{gate} is already approved; revoke it before recording a new decision")
    for prior in EXPECTED_GATES[: EXPECTED_GATES.index(gate)]:
        if not valid_human_gate(manifest, prior):
            raise PermissionError(f"{prior} must have explicit valid human approval before {gate}")
    if any(valid_human_gate(manifest, later) for later in EXPECTED_GATES[EXPECTED_GATES.index(gate) + 1 :]):
        raise ValueError("a downstream Gate is still approved; revoke the earlier Gate first")

    bindings: dict[str, Any] = {}
    if gate == "G1":
        selected = _note(selected_problem or "", "selected_problem")
        bindings["selected_problem"] = selected
    elif gate == "G2":
        route_id = _note(route_id or "", "route_id")
        problem_id = _note(problem_id or "", "problem_id")
        route_tree_path = (route_tree_path or root / "03_建模工作区/decisions/route-tree.json").resolve()
        if not route_tree_path.is_relative_to(root):
            raise ValueError("route tree must be inside the project")
        tree = load_tree(route_tree_path)
        node = next((item for item in tree["nodes"] if item["route_id"] == route_id), None)
        if tree["problem_id"] != problem_id or node is None:
            raise ValueError("problem_id/route_id do not identify a route in the current tree")
        if node["status"] != "quick_tested":
            raise ValueError("G2 may select only a reviewed and quick-tested route")
        bindings.update(problem_id=problem_id, route_id=route_id,
                        route_tree_sha256=tree_fingerprint(tree))

    approved_at = _timestamp_after_prior(records, gate)
    if stage.get("approved_at") or stage.get("approved_by"):
        stage.setdefault("approval_history", []).append(_stage_snapshot(stage))
    # The active workflow mode decides how much ceremony this Gate needs.  It is
    # read relative to the project being modified, not relative to the installed
    # scripts, so an isolated workspace uses its own setting.  The mode is recorded
    # with the decision; it never supplies or substitutes a human approval.  A
    # broken mode configuration falls back to the strictest tier instead of
    # failing open, so a damaged config can never make a Gate easier to pass.
    mode_path = root / "90_工具与配置/configs/workflow-mode.txt"
    try:
        active_mode = current_mode(mode_path)
        requirement = gate_requirement(gate, active_mode)
    except ModeError as error:
        print(f"gate_control: workflow mode unusable ({error}); assuming 'research'", file=sys.stderr)
        active_mode, requirement = "research", "required"
    stage.update(status="approved", approved_by=approver, approved_at=approved_at,
                 approval_note=note, workflow_mode=active_mode,
                 workflow_requirement=requirement, **bindings)

    state_path = root / "90_工具与配置/state/artifact_snapshots.json"
    bind_artifacts = requires_artifact_binding(gate, active_mode)
    for dependency in GATE_DEPENDENCIES[gate]:
        target = resolve_artifact(dependency, root)
        if bind_artifacts and not target.exists():
            raise FileNotFoundError(f"required Gate artifact is missing: {dependency}")
        if not bind_artifacts and not target.exists():
            # A lightweight Gate still reports what it could not bind, so the
            # lighter mode is visible in the record instead of silent.
            stage.setdefault("unbound_dependencies", []).append(dependency)
    staged_state = state_path.with_name(state_path.name + f".{os.getpid()}.staged")
    staged_state.unlink(missing_ok=True)
    approval_record = f"{approver} at {approved_at}"
    if state_path.exists():
        staged_state.parent.mkdir(parents=True, exist_ok=True)
        staged_state.write_bytes(state_path.read_bytes())
    try:
        if not requires_snapshot(gate, active_mode):
            # ``confirm`` (and any future lighter tier) records the human
            # decision without demanding a full artifact snapshot.  Existing
            # snapshots are left untouched.
            _replace_pair(manifest_path, manifest, state_path, staged_state)
        elif state_path.exists() and gate in load_json(state_path).get("snapshots", {}):
            recover(gate, path=staged_state, root=root, human_approval=approval_record)
            _replace_pair(manifest_path, manifest, state_path, staged_state)
        else:
            snapshot(gate, path=staged_state, root=root, human_approval=approval_record)
            _replace_pair(manifest_path, manifest, state_path, staged_state)
    finally:
        staged_state.unlink(missing_ok=True)
    return deepcopy(stage)


def revoke_gate(manifest_path: Path, gate: str, *, revoked_by: str, reason: str) -> list[str]:
    """Set this Gate and every downstream Gate pending, preserving prior records."""
    manifest_path = manifest_path.resolve()
    gate = _gate_id(gate)
    revoker = _human(revoked_by)
    reason = _note(reason, "reason")
    manifest = _validated_manifest(manifest_path)
    records = gate_records(manifest)
    revoked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    affected = list(EXPECTED_GATES[EXPECTED_GATES.index(gate) :])
    for current in affected:
        stage = records[current]
        stage.setdefault("revocations", []).append({
            "revoked_at": revoked_at,
            "revoked_by": revoker,
            "reason": reason,
            "previous": _stage_snapshot(stage),
            "trigger_gate": gate,
        })
        stage["status"] = "pending"
        stage["invalidation_reason"] = f"{gate} revoked by {revoker}: {reason}"
    dump_json(manifest_path, manifest)
    return affected


def gate_status(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    root = _root_for(manifest_path)
    manifest = _validated_manifest(manifest_path)
    records = gate_records(manifest)
    try:
        active_mode = current_mode(root / "90_工具与配置/configs/workflow-mode.txt")
    except ModeError:
        active_mode = "research"
    status: dict[str, Any] = {
        "_workflow_mode": active_mode,
        "_requirements": {gate: gate_requirement(gate, active_mode) for gate in EXPECTED_GATES},
    }
    for gate in EXPECTED_GATES:
        status[gate] = {
            "status": records[gate].get("status"),
            "approved_by": records[gate].get("approved_by"),
            "approved_at": records[gate].get("approved_at"),
            "workflow_requirement": gate_requirement(gate, active_mode),
            "valid_human_approval": valid_human_gate(manifest, gate),
        }
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Record explicit Human Gate decisions; never decides or auto-approves.")
    parser.add_argument("--manifest", type=Path, default=Path("run-manifest.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    approval = sub.add_parser("approve")
    approval.add_argument("gate", choices=EXPECTED_GATES)
    approval.add_argument("--approved-by", required=True)
    approval.add_argument("--note", required=True)
    approval.add_argument("--selected-problem")
    approval.add_argument("--route-id")
    approval.add_argument("--problem-id")
    approval.add_argument("--route-tree", type=Path)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("gate", choices=EXPECTED_GATES)
    revoke.add_argument("--revoked-by", required=True)
    revoke.add_argument("--reason", required=True)
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "approve":
        result = approve_gate(args.manifest, args.gate, approved_by=args.approved_by,
                              note=args.note, selected_problem=args.selected_problem,
                              route_id=args.route_id, problem_id=args.problem_id,
                              route_tree_path=args.route_tree)
    elif args.command == "revoke":
        result = {"pending": revoke_gate(args.manifest, args.gate,
                                          revoked_by=args.revoked_by, reason=args.reason)}
    else:
        result = gate_status(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
