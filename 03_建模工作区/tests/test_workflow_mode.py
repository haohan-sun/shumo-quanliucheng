"""Tests for the research / competition workflow-mode configuration layer.

The point of these tests is the boundary: a mode may change how much ceremony a
Gate needs, but it may never remove a Gate, weaken the submission Gate, or let
automation approve anything.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "90_工具与配置"
SCRIPTS = TOOLS / "scripts"
sys.path.insert(0, str(TOOLS))


def _config(requirements: dict[str, str]) -> dict:
    return {
        "schema_version": "1.0",
        "default_mode": "research",
        "modes": {"research": {"gates": {k: {"requirement": v} for k, v in requirements.items()}}},
    }


def test_shipped_configuration_is_valid():
    from scripts.workflow_mode import load_modes, validate_config

    assert validate_config(load_modes()) == []


def test_both_modes_keep_the_full_gate_inventory():
    from scripts.workflow_mode import GATES, mode_config

    for mode in ("research", "competition"):
        assert set(mode_config(mode)["gates"]) == set(GATES), mode


def test_default_mode_preserves_existing_behaviour():
    from scripts.workflow_mode import current_mode, gate_requirement, required_gates

    assert current_mode() == "research"
    assert gate_requirement("G4") == "required"
    assert len(required_gates()) == 7


def test_competition_mode_only_relaxes_baseline_and_figure():
    from scripts.workflow_mode import human_gates, required_gates

    assert set(required_gates("competition")) == {"G1", "G2", "G3", "G5", "G7"}
    # G4 and G6 are lighter, but remain human decisions.
    assert set(human_gates("competition")) == {"G1", "G2", "G3", "G4", "G5", "G6", "G7"}


def test_g7_is_never_weaker_than_confirm():
    from scripts.workflow_mode import gate_requirement, human_gates

    for mode in ("research", "competition"):
        assert gate_requirement("G7", mode) in {"required", "confirm"}
        assert "G7" in human_gates(mode)


def test_no_mode_can_auto_approve():
    from scripts.workflow_mode import GATES, gate_requirement

    for mode in ("research", "competition"):
        for gate in GATES:
            assert gate_requirement(gate, mode) in {"required", "confirm", "check"}
            if gate == "G7":
                assert gate_requirement(gate, mode) != "check"


def test_configuration_rejects_a_dropped_gate():
    from scripts.workflow_mode import validate_config

    errors = validate_config(_config({"G1": "required", "G2": "required"}))
    assert any("drops Human Gates" in error for error in errors)


def test_configuration_rejects_a_weakened_protected_gate():
    from scripts.workflow_mode import validate_config

    requirements = {f"G{n}": "required" for n in range(1, 8)}
    requirements["G7"] = "check"
    errors = validate_config(_config(requirements))
    assert any("protected gate G7" in error for error in errors)


def test_configuration_rejects_auto_approval():
    from scripts.workflow_mode import validate_config

    data = _config({f"G{n}": "required" for n in range(1, 8)})
    data["modes"]["research"]["gates"]["G4"]["auto_approvable"] = True
    errors = validate_config(data)
    assert any("auto_approvable" in error for error in errors)


def test_configuration_rejects_an_unknown_tier():
    from scripts.workflow_mode import validate_config

    requirements = {f"G{n}": "required" for n in range(1, 8)}
    requirements["G4"] = "skip"
    errors = validate_config(_config(requirements))
    assert any("invalid requirement" in error for error in errors)


def test_configuration_rejects_an_unknown_default_mode():
    from scripts.workflow_mode import validate_config

    data = _config({f"G{n}": "required" for n in range(1, 8)})
    data["default_mode"] = "sprint"
    assert any("default_mode" in error for error in validate_config(data))


def test_inventory_invariant_is_enforced():
    from scripts.workflow_mode import validate_config

    data = _config({f"G{n}": "required" for n in range(1, 8)})
    data["invariants"] = {"auto_approvable": False, "gate_inventory": ["G1", "G2"]}
    assert any("gate_inventory" in error for error in validate_config(data))


def test_switching_mode_does_not_edit_approval_records():
    from scripts.workflow_mode import GATES, gate_requirement

    before = (ROOT / "run-manifest.json").read_bytes()
    for mode in ("research", "competition"):
        for gate in GATES:
            gate_requirement(gate, mode)
    assert (ROOT / "run-manifest.json").read_bytes() == before


def test_mode_cli_validates_and_prints_both_modes():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "workflow_mode.py"), "--validate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "workflow_mode.py"), "--mode", "competition"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "G7" in result.stdout
    assert "confirm" in result.stdout
