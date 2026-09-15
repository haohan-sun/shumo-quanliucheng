from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, load_json, load_yaml

ROUTING_CONFIG = ROOT / "90_工具与配置" / "configs" / "auto-routing.yaml"
INVALID_APPROVERS = {"ai", "agent", "codex", "orchestrator", "hook", "skill", "subagent"}
EXPECTED_GATES = tuple(f"G{number}" for number in range(1, 8))


@dataclass(frozen=True)
class RouteDecision:
    action: str
    router: str
    primary_skill: str | None
    route: str | None
    stage: list[str]
    agents: list[str]
    review_agents: list[str]
    writer_scopes: list[str]
    missing_gates: list[str]
    gate: str | None
    postprocessors: list[str]
    reason_codes: list[str]
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    preprocessors: list[str] = field(default_factory=list)
    stale_artifacts: list[str] = field(default_factory=list)
    preflight_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def gate_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for stage in manifest.get("stages", []):
        match = re.match(r"^(G[1-7])\b", str(stage.get("name", "")), flags=re.IGNORECASE)
        if match:
            records[match.group(1).upper()] = stage
    return records


def valid_human_gate(manifest: dict[str, Any], gate_id: str) -> bool:
    record = gate_records(manifest).get(gate_id.upper())
    if not record or str(record.get("status", "")).casefold() != "approved":
        return False
    approver = str(record.get("approved_by", "")).strip()
    approved_at = str(record.get("approved_at", "")).strip()
    if not approver or normalize_text(approver) in INVALID_APPROVERS or not approved_at:
        return False
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def gate_inventory_errors(manifest: dict[str, Any]) -> list[str]:
    records = gate_records(manifest)
    missing = [gate for gate in EXPECTED_GATES if gate not in records]
    extra = sorted(set(records) - set(EXPECTED_GATES))
    errors = [f"missing required Human Gate: {gate}" for gate in missing]
    errors.extend(f"unexpected Human Gate: {gate}" for gate in extra)
    return errors


def _gate_intent(text: str, config: dict[str, Any]) -> str | None:
    for gate_id, terms in config.get("gate_intents", {}).items():
        if any(normalize_text(term) in text for term in terms):
            return gate_id
    return None


def _route_matches(text: str, config: dict[str, Any]) -> list[tuple[int, int, str, dict[str, Any]]]:
    matches: list[tuple[int, int, str, dict[str, Any]]] = []
    for name, route in config.get("routes", {}).items():
        matched = [
            normalize_text(term)
            for term in route.get("terms", [])
            if normalize_text(term) in text
        ]
        if matched:
            matches.append(
                (
                    int(route.get("priority", 0)),
                    max(len(term) for term in matched),
                    name,
                    route,
                )
            )
    return sorted(matches, key=lambda item: (-item[0], -item[1], item[2]))


def route_task(
    request: str,
    manifest: dict[str, Any] | None = None,
    *,
    project_related: bool = True,
    root: Path = ROOT,
) -> RouteDecision:
    config = load_yaml(ROUTING_CONFIG)
    state = deepcopy(manifest if manifest is not None else load_json(root / "run-manifest.json"))
    text = normalize_text(request)
    router = str(config.get("default_router", "mm-orchestrator"))
    if not project_related:
        return RouteDecision(
            "irrelevant", router, None, None, [], [], [], [], [], None, [], ["NOT_PROJECT_TASK"]
        )
    gate = _gate_intent(text, config)
    if gate:
        return RouteDecision(
            "stop_human_gate",
            router,
            None,
            None,
            [],
            [],
            [],
            [],
            [gate],
            gate,
            [],
            ["EXPLICIT_HUMAN_GATE_REQUIRED"],
        )
    matches = _route_matches(text, config)
    if not matches:
        return RouteDecision(
            "fallback_orchestrator",
            router,
            None,
            None,
            [],
            [],
            [],
            [],
            [],
            None,
            ["mm-ai-provenance"],
            ["NO_RELIABLE_FUNCTIONAL_MATCH"],
        )
    _, _, name, selected = matches[0]
    from scripts.artifact_state import invalidate_manifest

    stale = invalidate_manifest(
        state, path=root / "90_工具与配置/state/artifact_snapshots.json", root=root
    )
    missing = [
        gate_id
        for gate_id in selected.get("prerequisites", [])
        if not valid_human_gate(state, gate_id)
    ]
    action = "blocked_prerequisite" if missing else "route"
    return RouteDecision(
        action,
        router,
        str(selected["skill"]),
        name,
        list(selected.get("stage", [])),
        [] if missing else list(selected.get("agents", [])),
        [] if missing else list(selected.get("review_agents", [])),
        [] if missing else list(selected.get("writer_scopes", [])),
        missing,
        missing[0] if missing else None,
        [] if missing else list(dict.fromkeys([*selected.get("postprocessors", []), "mm-ai-provenance"])),
        ["PREREQUISITE_GATE_PENDING" if missing else "UNIQUE_PRIMARY_ROUTE"]
        + (["ARTIFACT_PASS_INVALIDATED"] if stale else []),
        list(selected.get("inputs", [])),
        list(selected.get("outputs", [])),
        [] if missing else list(selected.get("entrypoints", [])),
        [] if missing else list(selected.get("preprocessors", [])),
        stale,
        [] if missing else list(selected.get("preflight_skills", [])),
    )


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Preview deterministic AUTO routing guardrails.")
    parser.add_argument("request")
    parser.add_argument("--not-project", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            route_task(args.request, project_related=not args.not_project).to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
