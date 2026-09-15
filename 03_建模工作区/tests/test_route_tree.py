"""Executable bounded tournament contract; all probes are synthetic, no model search."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import ValidationError
from scripts import route_tree as rt

ROOT = Path(__file__).resolve().parents[2]


def add(tree, **kwargs):
    return rt.add_route(tree, hypothesis="human nominated hypothesis", model_family="LP", solver="highs", **kwargs)


def _tested(tree, score=.5, **kwargs):
    node = add(tree, **kwargs)
    rt.record_review(tree, node["route_id"], "bounded synthetic probe", .5)
    rt.record_quick_test(tree, node["route_id"], score)
    return node


def approval(tree, node):
    return {"stages": [{"name": "G2 model/method selection", "status": "approved",
                        "approved_by": "human user", "approved_at": "2026-09-05T12:00:00+08:00",
                        "problem_id": tree["problem_id"], "route_id": node["route_id"],
                        "route_tree_sha256": rt.tree_fingerprint(tree)}]}


def test_schema_roundtrip(tmp_path):
    tree = rt.new_tree("case")
    assert rt.load_tree(rt.save_tree(tree, tmp_path / "tree.json")) == tree
    _tested(tree)
    rt.validate_tree(tree)


@pytest.mark.parametrize("budget", [{"max_nodes": 0}, {"beam_width": 0}, {"max_quick_tests": -1}, {"typo": 2}])
def test_bad_budget(budget):
    with pytest.raises(ValidationError):
        rt.new_tree("case", budget)


def test_total_budget_not_refunded():
    tree = rt.new_tree("case", {"max_nodes": 1})
    node = add(tree)
    rt.prune(tree, node["route_id"], "data unavailable")
    with pytest.raises(rt.BudgetExceeded):
        add(tree)


def test_lifecycle_and_revision_invalidate_score():
    tree = rt.new_tree("case", {"max_quick_tests": 1})
    node = add(tree)
    with pytest.raises(ValueError):
        rt.record_quick_test(tree, node["route_id"], .8)
    rt.record_review(tree, node["route_id"], "risk", .6)
    rt.record_quick_test(tree, node["route_id"], .8)
    rt.revise(tree, node["route_id"], "changed assumption")
    assert node["quick_test_score"] is None
    assert rt.beam_survivors(tree, 0) == []
    rt.record_review(tree, node["route_id"], "risk", .6)
    with pytest.raises(rt.BudgetExceeded):
        rt.record_quick_test(tree, node["route_id"], .9)
    assert tree["used"]["quick_tests"] == 1


def test_beam_and_depth():
    tree = rt.new_tree("case", {"beam_width": 1, "max_depth": 1})
    loser, winner = _tested(tree, .2), _tested(tree, .8)
    with pytest.raises(ValueError):
        add(tree, parent=loser["route_id"])
    assert rt.prune_below_beam(tree, 0) == [loser["route_id"]]
    child = _tested(tree, .9, parent=winner["route_id"])
    assert child["depth"] == 1
    before = copy.deepcopy(tree)
    with pytest.raises(rt.BudgetExceeded):
        add(tree, parent=child["route_id"])
    assert tree == before
    with pytest.raises(ValueError):
        rt.revise(tree, winner["route_id"], "would stale descendant")


def test_untested_not_beam_candidate():
    tree = rt.new_tree("case")
    add(tree, expected_score=1)
    assert not rt.beam_survivors(tree, 0)
    with pytest.raises(ValueError):
        rt.prune_below_beam(tree, 0)


@pytest.mark.parametrize("value", [-.1, 1.1, float("nan"), float("inf")])
def test_invalid_score_is_atomic(value):
    tree = rt.new_tree("case")
    with pytest.raises(ValueError):
        add(tree, expected_score=value)
    assert tree["used"]["nodes"] == 0


def test_human_gate_and_closed_tree():
    tree = rt.new_tree("case")
    node = _tested(tree)
    with pytest.raises(PermissionError):
        rt.promote(tree, node["route_id"])
    manifest = approval(tree, node)
    wrong = copy.deepcopy(manifest)
    wrong["stages"][0]["approved_by"] = "codex"
    with pytest.raises(PermissionError):
        rt.promote(tree, node["route_id"], manifest=wrong)
    wrong["stages"][0]["approved_by"] = "human"
    wrong["stages"][0]["problem_id"] = "other case"
    with pytest.raises(PermissionError):
        rt.promote(tree, node["route_id"], manifest=wrong)
    before = copy.deepcopy(manifest)
    rt.promote(tree, node["route_id"], manifest=manifest)
    assert manifest == before
    rt.validate_tree(tree)
    with pytest.raises(ValueError):
        rt.record_review(tree, node["route_id"], "risk", .5)
    with pytest.raises(ValueError):
        add(tree)


def test_g2_approval_is_invalid_after_material_route_change():
    tree = rt.new_tree('case')
    node = _tested(tree)
    manifest = approval(tree, node)
    node['hypothesis'] = 'materially changed after approval'
    with pytest.raises(PermissionError, match='content hash'):
        rt.promote(tree, node['route_id'], manifest=manifest)


def test_tampered_tree_rejected():
    tree = rt.new_tree("case")
    node = _tested(tree)
    node["children"] = ["missing"]
    with pytest.raises(ValueError):
        rt.validate_tree(tree)


def test_cli(tmp_path):
    script = ROOT / "90_工具与配置/scripts/route_tree.py"
    tree = tmp_path / "tree.json"
    init = subprocess.run([sys.executable, str(script), "--tree", str(tree), "--init", "case"], capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    assert json.loads(init.stdout)["problem"] == "case"
    stats = subprocess.run([sys.executable, str(script), "--stats", str(tree)], capture_output=True, text=True)
    assert stats.returncode == 0, stats.stderr
    assert json.loads(stats.stdout)["used"] == {"nodes": 0, "quick_tests": 0}
    payload = tmp_path / "node.json"
    payload.write_text(json.dumps({"hypothesis": "h", "model_family": "LP", "solver": "highs"}), encoding="utf-8")
    added = subprocess.run([sys.executable, str(script), "--tree", str(tree), "--action", "add", "--payload", str(payload)], capture_output=True, text=True)
    assert added.returncode == 0, added.stderr
    assert rt.load_tree(tree)["used"]["nodes"] == 1
