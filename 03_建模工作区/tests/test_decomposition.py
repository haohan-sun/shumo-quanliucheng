"""Tests for lightweight task decomposition in front of the deterministic router.

The invariants under test are the ones that keep decomposition safe: it must not
replace the router, must not drop part of a request, must not bypass a Human Gate,
and must not let two writers own the same artifact without ordering.

Requests here are ASCII on purpose.  The classifier accepts both languages, but
routing tests should not depend on the console code page that a shell uses when it
passes arguments to a subprocess.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "90_工具与配置"
SCRIPTS = TOOLS / "scripts"
sys.path.insert(0, str(TOOLS))

# The router's own English terms, reused so a class decision here and the router's
# decision agree.
THREE_TASK_REQUEST = "data audit of missing values and robustness validation plus a figure"


def test_simple_request_bypasses_decomposition():
    from scripts.decompose import plan_request

    plan = plan_request("problem decomposition and assumption ledger")
    assert plan["decomposed"] is False
    assert plan["tasks"] == []
    assert plan["single_decision"]["primary_skill"] == "mm-problem-analysis"


def test_simple_request_returns_the_router_decision_unchanged():
    from scripts.auto_route import route_task
    from scripts.decompose import plan_request

    request = "mathematical derivation of the selected route"
    plan = plan_request(request)
    direct = route_task(request, project_related=True).to_dict()
    assert plan["decomposed"] is False
    assert plan["single_decision"]["primary_skill"] == direct["primary_skill"]
    assert plan["single_decision"]["action"] == direct["action"]


def test_unmatched_request_falls_back_to_the_router_not_to_an_empty_plan():
    from scripts.decompose import plan_request

    plan = plan_request("please take care of the remaining bits somehow")
    assert plan["decomposed"] is False
    assert plan["single_decision"] is not None
    assert plan["single_decision"]["action"] == "fallback_orchestrator"


def test_complex_request_decomposes_into_routed_tasks():
    from scripts.decompose import plan_request

    plan = plan_request(THREE_TASK_REQUEST)
    assert plan["decomposed"] is True
    classes = {task["task_class"] for task in plan["tasks"]}
    assert {"data", "validation", "figure"} <= classes
    for task in plan["tasks"]:
        assert task["primary_skill"], "every task must carry a router decision"
        assert task["action"] in {
            "route",
            "stop_human_gate",
            "blocked_prerequisite",
            "fallback_orchestrator",
            "irrelevant",
        }


def test_chinese_request_decomposes_too():
    """The classifier is bilingual; this is a classifier test, not a CLI test."""
    from scripts.decompose import atomic_tasks, classify

    assert classify("审计这批数据的缺失值") == "data"
    assert classify("检验稳健性和不确定性") == "validation"
    assert classify("出一张主结果图") == "figure"
    assert classify("写论文摘要初稿") == "paper"
    # Enumeration punctuation must not split one task into fragments.
    atoms = atomic_tasks("拆解这道题的变量、单位和约束")
    assert len(atoms) == 1
    assert atoms[0][0] == "problem"


def test_no_clause_is_silently_dropped():
    from scripts.decompose import _split_segments, atomic_tasks, plan_request

    request = "data audit of missing values and please also tidy the slide deck"
    segments = _split_segments(request)
    assert len(segments) == 2, segments
    atoms = atomic_tasks(request)
    assert len(atoms) == 2, "an unmatched clause must still become a task"
    assert any(task_class is None for task_class, _ in atoms)
    plan = plan_request(request)
    assert plan["decomposed"] is True
    assert len(plan["tasks"]) == 2


def test_each_task_uses_only_the_deterministic_router():
    from scripts import decompose

    calls: list[str] = []
    original = decompose.route_task

    def spy(request, manifest=None, **kwargs):
        calls.append(request)
        return original(request, manifest, **kwargs)

    decompose.route_task = spy
    try:
        plan = decompose.plan_request(THREE_TASK_REQUEST)
    finally:
        decompose.route_task = original
    assert calls, "the router must be consulted for every atomic task"
    assert len(calls) == len(plan["tasks"])


def test_decomposition_never_approves_a_gate():
    from scripts._project import load_json
    from scripts.auto_route import valid_human_gate
    from scripts.decompose import plan_request

    manifest_path = ROOT / "run-manifest.json"
    before = manifest_path.read_bytes()
    plan = plan_request("compare candidate route and then derive equations and then a figure")
    assert manifest_path.read_bytes() == before
    manifest = load_json(manifest_path)
    assert not any(valid_human_gate(manifest, f"G{n}") for n in range(1, 8))
    notes = " ".join(plan["notes"]).lower()
    assert "gate" in notes and "approved" in notes


def test_gate_prerequisites_are_reported_as_blockers():
    from scripts.decompose import plan_request

    plan = plan_request("compare candidate route and then write paper")
    assert plan["blocked_prerequisite"], (
        "route comparison needs G1, so the plan must report the missing prerequisite"
    )
    for item in plan["blocked_prerequisite"]:
        assert item["missing_gates"]


def test_gate_stops_are_surfaced_not_resolved():
    from scripts.decompose import plan_request

    plan = plan_request(THREE_TASK_REQUEST)
    assert isinstance(plan["gate_stops"], list)
    assert isinstance(plan["errors"], list)


def test_dependency_waves_are_acyclic_and_ordered():
    from scripts.decompose import plan_request

    plan = plan_request(THREE_TASK_REQUEST)
    steps = {task["task_id"]: task["step"] for task in plan["tasks"]}
    for task in plan["tasks"]:
        for parent in task["depends_on"]:
            assert steps[parent] < steps[task["task_id"]]
    assert plan["execution_waves"]


def test_writer_scopes_never_conflict_in_practice():
    from scripts.decompose import plan_request

    plan = plan_request(THREE_TASK_REQUEST)
    scopes = [task["writer_scope"] for task in plan["tasks"] if task["writer_scope"]]
    assert len(scopes) == len(set(scopes))
    assert plan["errors"] == []


def test_writer_scope_conflict_is_reported(monkeypatch):
    """Two writers sharing one artifact with no ordering must be an error.

    The generator chains tasks by canonical step, so a real conflict cannot arise
    by accident; this forces the pathological shape (two writers, same step, same
    scope) to prove the guard fires instead of silently serialising them.
    """
    from dataclasses import replace as dc_replace

    from scripts import decompose

    original = decompose._route_for
    counter = {"n": 0}

    def same_step(task_class, clause, manifest, root):
        decision = original(task_class, clause, manifest, root)
        counter["n"] += 1
        return dc_replace(
            decision, agents=["implementer" if counter["n"] % 2 else "reviewer"]
        )

    monkeypatch.setattr(decompose, "_route_for", same_step)
    monkeypatch.setitem(
        decompose.WRITER_SCOPES, "reviewer", decompose.WRITER_SCOPES["implementer"]
    )
    # Force both writers onto one step so neither depends on the other.
    original_step = decompose._step_of
    monkeypatch.setattr(decompose, "_step_of", lambda task_class: 7)

    plan = decompose.plan_request(THREE_TASK_REQUEST)
    monkeypatch.setattr(decompose, "_step_of", original_step)

    assert len(plan["tasks"]) >= 2
    assert all(not task["depends_on"] for task in plan["tasks"])
    assert any("writer scope conflict" in error for error in plan["errors"])


def test_route_decision_stays_frozen():
    """The router's value object is immutable; decomposition must not mutate it."""
    from dataclasses import FrozenInstanceError

    import pytest
    from scripts.auto_route import route_task

    decision = route_task("data audit of missing values")
    with pytest.raises(FrozenInstanceError):
        decision.reason_codes = ["mutated"]  # type: ignore[misc]


def test_plan_cli_emits_json():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "decompose.py"), THREE_TASK_REQUEST, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout.strip(), result.stderr
    payload = json.loads(result.stdout)
    assert payload["decomposed"] is True
    assert payload["execution_waves"]
    assert {task["task_class"] for task in payload["tasks"]} >= {"data", "validation", "figure"}


def test_plan_cli_human_output_lists_the_dag():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "decompose.py"), THREE_TASK_REQUEST],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in {0, 1}
    assert "task plan" in result.stdout
    assert "wave" in result.stdout
    assert "read-only" in result.stdout or "review" in result.stdout
