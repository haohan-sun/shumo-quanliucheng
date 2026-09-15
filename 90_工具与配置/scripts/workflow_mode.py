#!/usr/bin/env python3
"""Workflow modes: how much ceremony each Human Gate requires.

The project keeps G1-G7 as explicit human decisions in every mode.  Modes only
choose the *evidence* a Gate needs:

``required``
    Explicit human approval with full artifact binding (today's behaviour).
``confirm``
    Explicit human approval, lightweight: a named human and a note are still
    mandatory, but no extra artifact binding is demanded.
``check``
    A deterministic check only.  This is **not** an approval, and no mode may use
    it for the final submission Gate.

Guarantees enforced here and covered by ``test_workflow_mode.py``:

* every mode keeps all seven Gates in the inventory;
* no tier is auto-approvable -- automation can never pass a Gate;
* G7 may never be weaker than ``confirm``, so a mode cannot bypass submission
  approval;
* switching mode never edits approval records, and artifact-change invalidation
  stays mode-independent (``artifact_state`` owns that logic).

The default mode is ``research``, which reproduces the original behaviour, so
existing workspaces are unaffected.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import TOOLS_ROOT, load_yaml

CONFIG_PATH = TOOLS_ROOT / "configs" / "workflow-modes.yaml"
MODE_FILE = TOOLS_ROOT / "configs" / "workflow-mode.txt"
GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
REQUIREMENTS = ("required", "confirm", "check")
# A Gate at these tiers is a retained human decision.
HUMAN_TIERS = ("required", "confirm")
PROTECTED_GATES = ("G7",)
MINIMUM_TIER = {"G7": "confirm"}


class ModeError(RuntimeError):
    """Invalid mode configuration; always reported without a traceback."""


def load_modes(path: Path = CONFIG_PATH) -> dict:
    if not path.is_file():
        raise ModeError(f"workflow mode configuration is missing: {path.as_posix()}")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ModeError(f"{path.as_posix()} must contain a mapping")
    return data


def validate_config(data: dict) -> list[str]:
    """Return configuration errors; empty list means valid."""
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("workflow-modes.yaml: schema_version must be 1.0")
    modes = data.get("modes")
    if not isinstance(modes, dict) or not modes:
        errors.append("workflow-modes.yaml: 'modes' must be a non-empty mapping")
        return errors
    default = data.get("default_mode")
    if default not in modes:
        errors.append(f"workflow-modes.yaml: default_mode {default!r} is not a declared mode")
    for name, entry in modes.items():
        if not isinstance(entry, dict):
            errors.append(f"workflow-modes.yaml: mode {name!r} must be a mapping")
            continue
        gates = entry.get("gates")
        if not isinstance(gates, dict):
            errors.append(f"workflow-modes.yaml: mode {name!r} has no 'gates' mapping")
            continue
        missing = [gate for gate in GATES if gate not in gates]
        if missing:
            errors.append(
                f"workflow-modes.yaml: mode {name!r} drops Human Gates {', '.join(missing)}; "
                "every mode must keep the full G1-G7 inventory"
            )
        for gate, spec in gates.items():
            if gate not in GATES:
                errors.append(f"workflow-modes.yaml: mode {name!r} declares unknown gate {gate!r}")
                continue
            if not isinstance(spec, dict):
                errors.append(f"workflow-modes.yaml: mode {name!r} gate {gate} must be a mapping")
                continue
            requirement = spec.get("requirement")
            if requirement not in REQUIREMENTS:
                errors.append(
                    f"workflow-modes.yaml: mode {name!r} gate {gate} has invalid requirement "
                    f"{requirement!r}; expected one of {', '.join(REQUIREMENTS)}"
                )
                continue
            if spec.get("auto_approvable"):
                errors.append(
                    f"workflow-modes.yaml: mode {name!r} gate {gate} marks auto_approvable=true; "
                    "automation may never pass a Human Gate"
                )
            minimum = MINIMUM_TIER.get(gate)
            if minimum and REQUIREMENTS.index(requirement) > REQUIREMENTS.index(minimum):
                errors.append(
                    f"workflow-modes.yaml: mode {name!r} weakens protected gate {gate} to "
                    f"{requirement!r}; it must stay at least {minimum!r}"
                )
    invariants = data.get("invariants", {})
    if isinstance(invariants, dict):
        if invariants.get("auto_approvable"):
            errors.append("workflow-modes.yaml: invariants.auto_approvable must be false")
        inventory = invariants.get("gate_inventory")
        if inventory is not None and list(inventory) != list(GATES):
            errors.append("workflow-modes.yaml: invariants.gate_inventory must list G1-G7 in order")
    return errors


def current_mode(path: Path = MODE_FILE) -> str:
    """Active mode: ``configs/workflow-mode.txt`` when present, else the default."""
    data = load_modes()
    default = str(data.get("default_mode", "research"))
    if not path.is_file():
        return default
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        return default
    if value not in (data.get("modes") or {}):
        raise ModeError(
            f"{path.as_posix()} selects unknown mode {value!r}; "
            f"available: {', '.join(sorted(data.get('modes') or {}))}"
        )
    return value


def mode_config(mode: str | None = None) -> dict:
    data = load_modes()
    errors = validate_config(data)
    if errors:
        raise ModeError("; ".join(errors))
    selected = mode or current_mode()
    return data["modes"][selected]


def gate_requirement(gate: str, mode: str | None = None) -> str:
    if gate not in GATES:
        raise ModeError(f"unknown gate {gate!r}; expected one of {', '.join(GATES)}")
    config = mode_config(mode)
    return str(config["gates"][gate]["requirement"])


def required_gates(mode: str | None = None) -> list[str]:
    """Gates that need a full recorded human approval in this mode."""
    return [gate for gate in GATES if gate_requirement(gate, mode) == "required"]


def human_gates(mode: str | None = None) -> list[str]:
    """Every Gate that still needs an explicit human decision in this mode."""
    return [gate for gate in GATES if gate_requirement(gate, mode) in HUMAN_TIERS]


def describe(mode: str | None = None) -> str:
    config = mode_config(mode)
    selected = mode or current_mode()
    lines = [
        f"workflow mode: {selected} ({config.get('display_name', selected)})",
        "",
    ]
    for gate in GATES:
        spec = config["gates"][gate]
        lines.append(f"  {gate}  {spec['requirement']:<8} {spec.get('stage', '')}")
    lines.extend(
        [
            "",
            "  required = full human approval with artifact binding",
            "  confirm  = explicit human approval, lightweight note",
            "  check    = deterministic check only, never an approval",
            "",
            "  No mode lets automation approve a Gate; G7 is always a human decision.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or validate the workflow mode (research | competition)."
    )
    parser.add_argument("--mode", choices=["research", "competition"], help="Inspect a specific mode.")
    parser.add_argument("--validate", action="store_true", help="Validate the configuration only.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    try:
        data = load_modes()
    except ModeError as error:
        print(f"workflow mode: FAIL\n  {error}", file=sys.stderr)
        return 2
    errors = validate_config(data)
    if errors:
        print("workflow mode: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.validate:
        print("workflow mode: PASS")
        return 0
    if args.json:
        import json

        selected = args.mode or current_mode()
        print(
            json.dumps(
                {
                    "active_mode": current_mode(),
                    "inspected_mode": selected,
                    "gates": {
                        gate: {
                            "requirement": gate_requirement(gate, selected),
                            "human_decision_required": gate_requirement(gate, selected) in HUMAN_TIERS,
                        }
                        for gate in GATES
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(describe(args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
