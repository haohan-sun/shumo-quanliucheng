"""Workflow modes must really change Gate behaviour, not just the display.

These tests drive the real ``gate_control.approve_gate`` API in a temporary
project, so they fail if the mode layer stops being wired into Gate decisions.

Invariants that must hold in every mode:

* a Gate is never approved by automation;
* a ``confirm`` Gate is still an explicit human decision;
* G7 can never be weakened;
* switching mode never rewrites an existing approval.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "90_工具与配置"
sys.path.insert(0, str(TOOLS))

from scripts import artifact_state, workflow_mode  # noqa: E402
from scripts.gate_control import approve_gate, gate_status  # noqa: E402
from scripts.route_tree import (  # noqa: E402
    add_route,
    new_tree,
    record_quick_test,
    record_review,
    save_tree,
)

STATE_REL = "90_工具与配置/state/artifact_snapshots.json"


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal valid workspace, matching the layout gate_control expects."""
    for relative in (
        "01_题目与要求",
        "02_参考文献",
        "03_建模工作区/decisions",
        "03_建模工作区/model",
        "03_建模工作区/problem",
        "03_建模工作区/src",
        "03_建模工作区/results",
        "03_建模工作区/evidence",
        "03_建模工作区/experiments",
        "03_建模工作区/figures/final",
        "04_论文与提交/references",
        "04_论文与提交/ai_provenance",
        "90_工具与配置/configs",
        "90_工具与配置/state",
        "90_工具与配置/schemas",
    ):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "run-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {"stages": [{"name": f"G{i} gate", "type": "gate", "status": "pending"} for i in range(1, 8)]}
        ),
        encoding="utf-8",
    )
    (tmp_path / "03_建模工作区/decisions/DECISION_LOG.md").write_text("# log\n", encoding="utf-8")
    (tmp_path / "03_建模工作区/problem/PROBLEM_ANALYSIS.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "03_建模工作区/model/HUMAN_MODEL_IDEAS.md").write_text("ideas\n", encoding="utf-8")
    (tmp_path / "03_建模工作区/model/MODEL_SPEC.md").write_text("Status: DRAFT\n", encoding="utf-8")
    (tmp_path / "03_建模工作区/results/results.json").write_text(
        '{"schema_version": "1.0", "results": []}\n', encoding="utf-8"
    )
    (tmp_path / "03_建模工作区/evidence/EVIDENCE_PASSPORT.yaml").write_text(
        "schema_version: '1.0'\nrecords: []\n", encoding="utf-8"
    )
    (tmp_path / "03_建模工作区/experiments/registry.csv").write_text("experiment_id\n", encoding="utf-8")
    (tmp_path / "03_建模工作区/figures/manifest.json").write_text(
        '{"schema_version": "1.0", "figures": []}\n', encoding="utf-8"
    )
    (tmp_path / "04_论文与提交/references/references.json").write_text(
        '{"schema_version": "1.0", "references": []}\n', encoding="utf-8"
    )
    (tmp_path / "04_论文与提交/ai_provenance/ledger.yaml").write_text(
        "schema_version: '1.0'\nrecords: []\n", encoding="utf-8"
    )
    (tmp_path / "90_工具与配置/configs/workspace-layout.yaml").write_text(
        'schema_version: "1.0"\nworkspace_root: "."\ntool_root: "90_工具与配置"\n'
        'work_root: "03_建模工作区"\npaper_root: "04_论文与提交"\n'
        'sources:\n  problem_roots: []\n  literature_roots: []\n  requirement_files: []\n',
        encoding="utf-8",
    )
    tree = new_tree("problem-A")
    node = add_route(tree, hypothesis="h", model_family="LP", solver="highs")
    record_review(tree, node["route_id"], "bounded risk", 0.7)
    record_quick_test(tree, node["route_id"], 0.8)
    save_tree(tree, tmp_path / "03_建模工作区/decisions/route-tree.json")
    return manifest_path, tmp_path / "03_建模工作区/decisions/route-tree.json"


def _mode_file(tmp_path: Path) -> Path:
    return tmp_path / "90_工具与配置/configs/workflow-mode.txt"


def _approve_through(manifest: Path, tmp_path: Path, mode: str, last: str) -> None:
    """Approve G1..G<last> through the real API under the given mode."""
    workflow_mode.set_mode(mode, _mode_file(tmp_path))
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    approve_gate(manifest, "G2", approved_by="Alice", note="route chosen",
                 problem_id="problem-A", route_id="R01")
    if last == "G2":
        return
    approve_gate(manifest, "G3", approved_by="Alice", note="spec frozen")
    if last == "G3":
        return
    approve_gate(manifest, "G4", approved_by="Alice", note="baseline accepted")
    if last == "G4":
        return
    approve_gate(manifest, "G5", approved_by="Alice", note="results frozen")


def _snapshots(tmp_path: Path) -> list[str]:
    state = tmp_path / STATE_REL
    if not state.is_file():
        return []
    return sorted(json.loads(state.read_text(encoding="utf-8"))["snapshots"])


def _stage(manifest: Path, index: int) -> dict:
    return json.loads(manifest.read_text(encoding="utf-8"))["stages"][index]


def test_research_mode_keeps_the_full_behaviour(project):
    manifest, _ = project
    tmp_path = manifest.parent
    _approve_through(manifest, tmp_path, "research", "G5")
    assert _snapshots(tmp_path) == ["G1", "G2", "G3", "G4", "G5"]
    for index in range(5):
        assert _stage(manifest, index)["workflow_requirement"] == "required"


def test_competition_mode_lightens_only_g4_and_g6(project):
    manifest, _ = project
    tmp_path = manifest.parent
    _approve_through(manifest, tmp_path, "competition", "G5")
    # G1, G2, G3 and G5 are still `required`; only G4 is lighter.
    assert _snapshots(tmp_path) == ["G1", "G2", "G3", "G5"]
    assert _stage(manifest, 3)["workflow_requirement"] == "confirm"
    assert _stage(manifest, 3)["status"] == "approved"
    assert _stage(manifest, 0)["workflow_requirement"] == "required"
    assert _stage(manifest, 2)["workflow_requirement"] == "required"
    assert _stage(manifest, 4)["workflow_requirement"] == "required"


def test_confirm_gate_is_still_a_human_decision(project):
    manifest, _ = project
    tmp_path = manifest.parent
    workflow_mode.set_mode("competition", _mode_file(tmp_path))
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    approve_gate(manifest, "G2", approved_by="Alice", note="route", problem_id="problem-A",
                 route_id="R01")
    approve_gate(manifest, "G3", approved_by="Alice", note="frozen")
    # The lighter tier still refuses AI approvers and still needs a note.
    with pytest.raises(PermissionError):
        approve_gate(manifest, "G4", approved_by="Codex agent", note="auto")
    with pytest.raises(ValueError):
        approve_gate(manifest, "G4", approved_by="Alice", note="")
    approved = approve_gate(manifest, "G4", approved_by="Alice", note="baseline ok")
    assert approved["approved_by"] == "Alice"
    assert approved["workflow_mode"] == "competition"


def test_required_gate_in_competition_mode_still_needs_its_artifact(project):
    manifest, _ = project
    tmp_path = manifest.parent
    workflow_mode.set_mode("competition", _mode_file(tmp_path))
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    approve_gate(manifest, "G2", approved_by="Alice", note="route", problem_id="problem-A",
                 route_id="R01")
    (tmp_path / "03_建模工作区/model/MODEL_SPEC.md").unlink()
    with pytest.raises(FileNotFoundError, match="MODEL_SPEC"):
        approve_gate(manifest, "G3", approved_by="Alice", note="frozen")


def test_confirm_gate_records_what_it_could_not_bind(project, monkeypatch):
    """A lighter Gate reports the dependency it could not bind, instead of hiding it."""
    manifest, _ = project
    tmp_path = manifest.parent
    # Add a dependency that genuinely does not exist, so the recording path is
    # exercised without having to delete a fixture the other gates rely on.
    monkeypatch.setitem(
        artifact_state.GATE_DEPENDENCIES,
        "G4",
        [*artifact_state.GATE_DEPENDENCIES["G4"], "03_建模工作区/results/not_there.json"],
    )
    workflow_mode.set_mode("competition", _mode_file(tmp_path))
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    approve_gate(manifest, "G2", approved_by="Alice", note="route", problem_id="problem-A",
                 route_id="R01")
    approve_gate(manifest, "G3", approved_by="Alice", note="frozen")
    approve_gate(manifest, "G4", approved_by="Alice", note="baseline ok")
    stage = _stage(manifest, 3)
    assert stage["status"] == "approved"
    assert any("not_there.json" in entry for entry in stage["unbound_dependencies"])


def test_g7_is_never_weakened(project):
    for mode in ("research", "competition"):
        assert workflow_mode.gate_requirement("G7", mode) in {"required", "confirm"}
        assert workflow_mode.is_human_decision("G7", mode) is True


def test_switching_mode_does_not_rewrite_approvals(project):
    manifest, _ = project
    tmp_path = manifest.parent
    _approve_through(manifest, tmp_path, "research", "G3")
    before = manifest.read_bytes()
    workflow_mode.set_mode("competition", _mode_file(tmp_path))
    assert manifest.read_bytes() == before
    workflow_mode.set_mode("research", _mode_file(tmp_path))
    assert manifest.read_bytes() == before
    # The recorded requirement keeps describing the mode in force at approval time.
    assert _stage(manifest, 2)["workflow_mode"] == "research"


def test_gate_status_reports_validity_for_every_gate(project):
    manifest, _ = project
    tmp_path = manifest.parent
    _approve_through(manifest, tmp_path, "competition", "G4")
    status = gate_status(manifest)
    gates = [key for key in status if not key.startswith("_")]
    assert sorted(gates) == [f"G{n}" for n in range(1, 8)]
    assert status["_workflow_mode"] == "competition"
    assert status["_requirements"]["G4"] == "confirm"
    assert status["G4"]["valid_human_approval"] is True
    assert status["G4"]["workflow_requirement"] == "confirm"
    assert status["G5"]["valid_human_approval"] is False


def test_a_broken_mode_file_cannot_make_a_gate_easier(project):
    manifest, _ = project
    tmp_path = manifest.parent
    mode_file = _mode_file(tmp_path)
    mode_file.parent.mkdir(parents=True, exist_ok=True)
    mode_file.write_text("does-not-exist\n", encoding="utf-8")
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    # Reads fall back to the strictest tier instead of failing open.
    assert workflow_mode.gate_requirement("G4") in {"required", "confirm"}


def test_shipped_mode_file_is_restored_after_tests():
    """These tests must not leave the repository on a non-default mode."""
    assert workflow_mode.current_mode() == "research"
