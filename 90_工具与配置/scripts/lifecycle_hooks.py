from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, dump_json, load_json, load_yaml
from scripts.artifact_state import sync_manifest
from scripts.build_ai_usage_report import build as build_ai_report
from scripts.build_ai_usage_report import validate_ledger
from scripts.doctor import inspect_environment
from scripts.status import collect_status
from scripts.validate_contracts import validate_project
from scripts.verify_structure import verify

TOOLS_RELATIVE = Path("90_工具与配置")
PAPER_RELATIVE = Path("04_论文与提交")
FORBIDDEN_EVENT_FIELDS = {
    "chain_of_thought",
    "hidden_prompt",
    "reasoning",
    "secret",
    "transcript",
}
STOP_GUARD_TESTS = (
    "03_建模工作区/tests/test_agents.py",
    "03_建模工作区/tests/test_artifact_state.py",
    "03_建模工作区/tests/test_auto_routing.py",
    "03_建模工作区/tests/test_package_guard.py",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _event_directory(root: Path) -> Path:
    return root / TOOLS_RELATIVE / "reports" / "provenance" / "events"


def _safe_digest(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def event_record(payload: dict[str, Any], *, timestamp: str | None = None) -> dict[str, Any]:
    record = {
        "event": str(payload.get("hook_event_name", "unknown")),
        "recorded_at": timestamp or utc_now(),
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "agent_id": payload.get("agent_id"),
        "agent_type": payload.get("agent_type"),
        "model": payload.get("model"),
        "permission_mode": payload.get("permission_mode"),
        "message_sha256": _safe_digest(payload.get("last_assistant_message")),
    }
    return {key: value for key, value in record.items() if value is not None}


def write_event(payload: dict[str, Any], root: Path = ROOT) -> Path:
    record = event_record(payload)
    if FORBIDDEN_EVENT_FIELDS & set(record):
        raise ValueError("provenance event contains a forbidden field")
    directory = _event_directory(root)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = record["recorded_at"].replace(":", "-")
    path = directory / f"{stamp}-{uuid.uuid4().hex}.json"
    dump_json(path, record)
    return path


def provenance_pair_errors(root: Path = ROOT) -> list[str]:
    directory = _event_directory(root)
    if not directory.is_dir():
        return []
    balances: dict[str, int] = {}
    errors: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            record = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid provenance event {path.name}: {exc}")
            continue
        forbidden = FORBIDDEN_EVENT_FIELDS & set(record)
        if forbidden:
            errors.append(f"forbidden provenance fields in {path.name}: {sorted(forbidden)}")
        agent_id = str(record.get("agent_id", ""))
        if not agent_id:
            continue
        if record.get("event") == "SubagentStart":
            balances[agent_id] = balances.get(agent_id, 0) + 1
        elif record.get("event") == "SubagentStop":
            balances[agent_id] = balances.get(agent_id, 0) - 1
    errors.extend(
        f"unpaired subagent lifecycle metadata for {agent_id}: balance={balance}"
        for agent_id, balance in sorted(balances.items())
        if balance != 0
    )
    return errors


def _update_orchestration(root: Path, **changes: Any) -> None:
    path = root / "run-manifest.json"
    manifest = load_json(path)
    orchestration = manifest.setdefault("orchestration", {})
    orchestration.update(changes)
    dump_json(path, manifest)


def _sync_artifact_state(root: Path) -> list[str]:
    path = root / "run-manifest.json"
    manifest = load_json(path)
    stale = sync_manifest(
        manifest, path=root / TOOLS_RELATIVE / "state" / "artifact_snapshots.json", root=root
    )
    dump_json(path, manifest)
    return stale


def _write_status_snapshot(
    root: Path, status: dict[str, Any], checks: dict[str, Any]
) -> Path:
    path = root / TOOLS_RELATIVE / "reports" / "session-status.json"
    dump_json(path, {"checked_at": utc_now(), "status": status, "checks": checks})
    return path


def session_start(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    stale = _sync_artifact_state(root)
    structure_errors = verify(root)
    contract_errors = validate_project(root)
    status = collect_status(root)
    checked_at = utc_now()
    checks = {
        "structure_ok": not structure_errors,
        "contracts_ok": not contract_errors,
        "errors": [*structure_errors, *contract_errors],
        "invalidated_passes": stale,
    }
    _write_status_snapshot(root, status, checks)
    _update_orchestration(root, last_state_check=checked_at)
    gate_state = {
        stage["name"].split()[0]: stage.get("status")
        for stage in load_json(root / "run-manifest.json").get("stages", [])
        if str(stage.get("name", "")).startswith("G")
    }
    context = (
        "AUTO-ORCHESTRATED MODE is active. Inspect state and route every non-trivial project "
        "task through mm-orchestrator. Current project status: "
        f"{status['status']}; model={status['model_status']}; gates={gate_state}. "
        f"State checks={'PASS' if not checks['errors'] else 'FAIL'}. Never auto-approve a Gate."
    )
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }


def subagent_start(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    write_event(payload, root)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": (
                "Follow AUTO routing, remain within the selected role, and respect one-writer "
                "artifact ownership. Never edit Gate approval fields or hidden reasoning logs."
            ),
        }
    }


def subagent_stop(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    write_event(payload, root)
    return {"continue": True}


def stop_checks(root: Path = ROOT) -> tuple[list[str], bool]:
    errors: list[str] = []
    stale = _sync_artifact_state(root)
    errors.extend(f"artifact invalidation: {item}" for item in stale)
    environment = inspect_environment()
    if not environment["required_ok"]:
        errors.append("environment check failed")
    errors.extend(verify(root))
    errors.extend(validate_project(root))
    try:
        test_paths = [str(root / path) for path in STOP_GUARD_TESTS if (root / path).is_file()]
        if not test_paths:
            raise FileNotFoundError("no lifecycle guard tests found")
        test = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *test_paths], cwd=root, capture_output=True,
            text=True, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=120,
        )
        if test.returncode:
            detail = (test.stdout + test.stderr).strip()[-2000:]
            errors.append(f"pytest failed: {detail}")
    except subprocess.TimeoutExpired:
        errors.append("pytest timed out after 120 seconds")
    ledger_path = root / PAPER_RELATIVE / "ai_provenance" / "ledger.yaml"
    ledger_errors = validate_ledger(load_yaml(ledger_path))
    report_errors = build_ai_report(root, check=True)
    provenance_errors = [*ledger_errors, *report_errors, *provenance_pair_errors(root)]
    errors.extend(f"provenance: {error}" for error in provenance_errors)
    checked_at = utc_now()
    _update_orchestration(
        root,
        last_validation=checked_at,
        last_validation_ok=not errors,
        last_provenance_check=checked_at,
    )
    _write_status_snapshot(
        root,
        collect_status(root),
        {
            "validation_ok": not errors,
            "provenance_ok": not provenance_errors,
            "errors": errors,
        },
    )
    return errors, not provenance_errors


def stop(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    errors, _ = stop_checks(root)
    if errors and not payload.get("stop_hook_active"):
        return {
            "decision": "block",
            "reason": "AUTO validation failed; fix these deterministic checks: "
            + " | ".join(errors[:5]),
        }
    return {
        "continue": True,
        "systemMessage": (
            "AUTO validation passed."
            if not errors
            else "AUTO validation still has findings; Stop re-entry guard prevented a loop."
        ),
    }


def dispatch(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        return session_start(payload, root)
    if event == "SubagentStart":
        return subagent_start(payload, root)
    if event == "SubagentStop":
        return subagent_stop(payload, root)
    if event == "Stop":
        return stop(payload, root)
    return {"continue": True}


def main() -> int:
    payload: dict[str, Any] = {}
    try:
        payload = json.load(sys.stdin)
        output = dispatch(payload)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except Exception as exc:
        is_stop = payload.get("hook_event_name") == "Stop"
        print(
            json.dumps(
                {
                    **({
                        "decision": "block",
                        "reason": f"AUTO lifecycle Stop hook failed: {type(exc).__name__}",
                    } if is_stop else {
                        "continue": True,
                        "systemMessage": f"AUTO lifecycle hook failed visibly: {type(exc).__name__}",
                    }),
                },
                ensure_ascii=False,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
