import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.gate_control import approve_gate, gate_status, revoke_gate
from scripts.route_tree import add_route, new_tree, record_quick_test, record_review, save_tree

ROOT = Path(__file__).resolve().parents[2]


def project(tmp_path: Path) -> tuple[Path, Path]:
    for path in ("01_题目与要求", "03_建模工作区/decisions", "03_建模工作区/problem",
                 "03_建模工作区/model", "03_建模工作区/src", "03_建模工作区/results",
                 "03_建模工作区/figures/final", "04_论文与提交/paper",
                 "90_工具与配置/state"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    manifest = {
        "stages": [{"name": f"G{i} gate", "type": "gate", "status": "pending"}
                   for i in range(1, 8)]
    }
    manifest_path = tmp_path / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "03_建模工作区/decisions/DECISION_LOG.md").write_text(
        "# Human decisions\n", encoding="utf-8"
    )
    (tmp_path / "03_建模工作区/problem/PROBLEM_ANALYSIS.json").write_text("{}", encoding="utf-8")
    (tmp_path / "03_建模工作区/model/HUMAN_MODEL_IDEAS.md").write_text("ideas", encoding="utf-8")
    tree = new_tree("problem-A")
    node = add_route(tree, hypothesis="h", model_family="LP", solver="highs")
    record_review(tree, node["route_id"], "bounded risk", .7)
    record_quick_test(tree, node["route_id"], .8)
    save_tree(tree, tmp_path / "03_建模工作区/decisions/route-tree.json")
    return manifest_path, tmp_path / "03_建模工作区/decisions/route-tree.json"


def test_approval_requires_human_note_order_and_problem(tmp_path):
    manifest, _ = project(tmp_path)
    original = manifest.read_bytes()
    with pytest.raises(PermissionError):
        approve_gate(manifest, "G1", approved_by="Codex agent", note="chosen", selected_problem="A")
    with pytest.raises(ValueError):
        approve_gate(manifest, "G1", approved_by="Alice", note="", selected_problem="A")
    with pytest.raises(ValueError):
        approve_gate(manifest, "G1", approved_by="Alice", note="chosen")
    with pytest.raises(PermissionError):
        approve_gate(manifest, "G2", approved_by="Alice", note="chosen",
                     problem_id="problem-A", route_id="R01")
    assert manifest.read_bytes() == original
    approved = approve_gate(manifest, "G1", approved_by="Alice", note="explicit choice",
                            selected_problem="A")
    assert approved["selected_problem"] == "A"
    assert gate_status(manifest)["G1"]["valid_human_approval"] is True
    assert json.loads((tmp_path / "90_工具与配置/state/artifact_snapshots.json").read_text(encoding="utf-8"))["snapshots"]["G1"]


def test_g2_binds_current_tree_and_resnapshot(tmp_path):
    manifest, tree_path = project(tmp_path)
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    with pytest.raises(ValueError):
        approve_gate(manifest, "G2", approved_by="Alice", note="chosen",
                     problem_id="wrong", route_id="R01", route_tree_path=tree_path)
    record = approve_gate(manifest, "G2", approved_by="Alice", note="explicit method",
                          problem_id="problem-A", route_id="R01", route_tree_path=tree_path)
    assert len(record["route_tree_sha256"]) == 64
    saved = json.loads(manifest.read_text())
    assert saved["stages"][1]["route_id"] == "R01"


def test_failed_snapshot_is_atomic(tmp_path):
    manifest, _ = project(tmp_path)
    # Remove a required artifact after manifest creation: approval must not leak to disk.
    (tmp_path / "01_题目与要求").rmdir()
    before = manifest.read_bytes()
    with pytest.raises(Exception):
        approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    assert manifest.read_bytes() == before
    assert not (tmp_path / "90_工具与配置/state/artifact_snapshots.json").exists()


def test_revoke_preserves_approval_and_invalidates_downstream(tmp_path):
    manifest, tree_path = project(tmp_path)
    approve_gate(manifest, "G1", approved_by="Alice", note="chosen", selected_problem="A")
    approve_gate(manifest, "G2", approved_by="Alice", note="method", problem_id="problem-A",
                 route_id="R01", route_tree_path=tree_path)
    before = copy.deepcopy(json.loads(manifest.read_text())["stages"][0])
    affected = revoke_gate(manifest, "G1", revoked_by="Bob", reason="official correction")
    saved = json.loads(manifest.read_text())
    assert affected == [f"G{i}" for i in range(1, 8)]
    assert all(stage["status"] == "pending" for stage in saved["stages"])
    assert saved["stages"][0]["approved_by"] == before["approved_by"]
    assert saved["stages"][0]["approved_at"] == before["approved_at"]
    assert saved["stages"][0]["revocations"][-1]["previous"]["status"] == "approved"


def test_cli_status_is_read_only(tmp_path):
    manifest, _ = project(tmp_path)
    before = manifest.read_bytes()
    result = subprocess.run([
        sys.executable, str(ROOT / "90_工具与配置/scripts/gate_control.py"),
        "--manifest", str(manifest), "status",
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["G7"]["status"] == "pending"
    assert manifest.read_bytes() == before


def test_manifest_gate_order_and_time_are_validated(tmp_path):
    manifest, _ = project(tmp_path)
    data = json.loads(manifest.read_text())
    data["stages"][0], data["stages"][1] = data["stages"][1], data["stages"][0]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="G1-G7 order"):
        gate_status(manifest)

    manifest, _ = project(tmp_path)
    data = json.loads(manifest.read_text())
    data["stages"][0].update(status="approved", approved_by="Alice",
                              approved_at="2999-01-01T00:00:00+00:00")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="future"):
        approve_gate(manifest, "G2", approved_by="Bob", note="method",
                     problem_id="problem-A", route_id="R01")
