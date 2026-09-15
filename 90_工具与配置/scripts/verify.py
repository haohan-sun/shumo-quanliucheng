#!/usr/bin/env python3
"""Deterministic project verification.

``verify`` runs the project's real verification chain and reports what it found.
It deliberately does **not** write ``reports/verify.json`` and it never claims an
independent verification: per ``schemas/verify.schema.json`` and
``validate_contracts.py``, ``status: verified`` requires a named independent
reviewer and a human-recorded timestamp.  A machine run may only produce
``status: pending`` plus its check list; that is what ``--write-report`` writes
(to ``reports/verify-run.json``, so the human-owned record is never clobbered).

Checks reuse existing modules; nothing is reimplemented here:

* structure        -> ``verify_structure.verify``
* contracts        -> ``validate_contracts.validate_project``
* gate records     -> ``auto_route.gate_inventory_errors`` + ``valid_human_gate``
* artifact state   -> ``artifact_state.invalidate``
* claim registry   -> ``claim_registry.check_registry`` (skipped when absent)
* AI provenance    -> ``build_ai_usage_report.build``
* hook provenance  -> ``lifecycle_hooks.provenance_pair_errors``
* compliance       -> ``compliance.collect_findings`` (submission profile)
* package boundary -> ``build_submission.readiness_blockers``
* tests            -> ``pytest`` (only with ``--with-tests``)
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, TOOLS_ROOT, dump_json, load_json

REPORT_PATH = TOOLS_ROOT / "reports" / "verify-run.json"
PASS = "pass"
FAIL = "fail"
SKIP = "not_applicable"
# A workspace before the contest starts legitimately has no claim registry, no
# contest configuration and no approvals.  Those are reported as pending work,
# not as verification failures -- but they are never silently dropped either.
PENDING = "pending"
PENDING_PREFIX = "pending: "
NOTE_PREFIX = "note: "


def _check_structure(root: Path) -> list[str]:
    from scripts.verify_structure import verify

    return verify(root)


def _check_contracts(root: Path) -> list[str]:
    from scripts.validate_contracts import validate_project

    return validate_project(root)


def _check_gates(root: Path) -> list[str]:
    from scripts.auto_route import (
        EXPECTED_GATES,
        gate_inventory_errors,
        gate_records,
        valid_human_gate,
    )

    manifest = load_json(root / "run-manifest.json")
    errors = list(gate_inventory_errors(manifest))
    if errors:
        return errors
    records = gate_records(manifest)
    approved = [gate for gate in EXPECTED_GATES if valid_human_gate(manifest, gate)]
    for gate in EXPECTED_GATES:
        stage = records[gate]
        if str(stage.get("status", "")).lower() == "approved" and gate not in approved:
            errors.append(
                f"{gate} is marked approved but is not a valid human approval "
                "(requires status/approved_by/approved_at from a human)"
            )
    if not approved:
        errors.append(PENDING_PREFIX + "no Human Gate approved yet (expected before G1)")
    return errors


def _check_artifact_state(root: Path) -> list[str]:
    from scripts.artifact_state import invalidate

    return invalidate(root=root)


def _check_claims(root: Path) -> list[str]:
    registry = root / "04_论文与提交/paper/claim_registry.jsonl"
    if not registry.is_file():
        return [PENDING_PREFIX + "no claim registry yet (04_论文与提交/paper/claim_registry.jsonl)"]
    from scripts.claim_registry import check_registry

    return list(check_registry(registry, root=root))


def _check_ai_provenance(root: Path) -> list[str]:
    ledger = root / "04_论文与提交/ai_provenance/ledger.yaml"
    if not ledger.is_file():
        return [PENDING_PREFIX + "AI provenance ledger is missing: 04_论文与提交/ai_provenance/ledger.yaml"]
    from scripts.build_ai_usage_report import build

    errors = list(build(root=root, check=True))
    return [
        PENDING_PREFIX + item if item.startswith("stale or missing generated report") else item
        for item in errors
    ]


def _check_hook_provenance(root: Path) -> list[str]:
    from scripts.lifecycle_hooks import provenance_pair_errors

    return list(provenance_pair_errors(root=root))


# Findings that describe "this workspace has not finished a contest yet" rather
# than "something is inconsistent".  They must stay visible but must not make a
# fresh clone look broken.
PENDING_FINDING_CODES = frozenset(
    {
        "CONTEST_UNASSIGNED",
        "RULES_MISSING",
        "CONTROL_NUMBER_MISSING",
        "PAPER_PDF_UNSET",
        "PAPER_PDF_MISSING",
        "INDEPENDENT_VERIFICATION_PENDING",
        "AI_DISCLOSURE_MISSING",
        "SUPPORTING_MATERIAL_MISSING",
        "CONTEST_CONFIG_MISSING",
    }
)
PENDING_BLOCKER_PREFIXES = (
    "G7 ready-to-submit lacks explicit human approval",
    "90_工具与配置/reports/verify.json is not independently verified",
    "independent verification record is missing",
)


def _classify(items: list[str]) -> list[str]:
    """Mark expected pre-contest findings as pending instead of failures."""
    marked: list[str] = []
    for item in items:
        if item.startswith(PENDING_PREFIX):
            marked.append(item)
            continue
        code = item.split(":", 1)[0]
        if code in PENDING_FINDING_CODES or item.startswith(PENDING_BLOCKER_PREFIXES):
            marked.append(PENDING_PREFIX + item)
        else:
            marked.append(item)
    return marked


def _check_compliance(root: Path) -> list[str]:
    from scripts.compliance import collect_findings

    return _classify(
        [
            f"{finding['code']}: {finding['message']}"
            for finding in collect_findings(root, submission=True)
            if finding["level"] == "BLOCKER"
        ]
    )


def _check_package_boundary(root: Path) -> list[str]:
    from scripts.build_submission import readiness_blockers

    return _classify(list(readiness_blockers(root)))


def _check_tests(root: Path) -> tuple[str, list[str]]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    tail = [line for line in result.stdout.strip().splitlines() if line.strip()][-1:]
    evidence = tail or ["pytest produced no summary line"]
    if result.returncode:
        evidence.append(f"pytest exited {result.returncode}")
        if result.stderr.strip():
            evidence.append(result.stderr.strip().splitlines()[-1])
        return FAIL, evidence
    return PASS, evidence


CHECKS = (
    ("structure", "Required directories, files, agents and skill front matter", _check_structure),
    ("contracts", "JSON/YAML contracts, registries and cross-artifact links", _check_contracts),
    ("human_gates", "G1-G7 inventory and human-approval validity", _check_gates),
    ("artifact_state", "Approved gates whose artifacts changed after approval", _check_artifact_state),
    ("claim_registry", "Every paper number bound to a successful tracked run", _check_claims),
    ("ai_provenance", "AI-use ledger and generated disclosure reports", _check_ai_provenance),
    ("hook_provenance", "Subagent event pairing and forbidden event fields", _check_hook_provenance),
    ("compliance", "Submission blockers from official-rule checks", _check_compliance),
    ("package_boundary", "Submission readiness through the full guard chain", _check_package_boundary),
)


def _triage(items: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split evidence into (failures, pending, notes)."""
    failures: list[str] = []
    pending: list[str] = []
    notes: list[str] = []
    for item in items:
        if item.startswith(PENDING_PREFIX):
            pending.append(item[len(PENDING_PREFIX) :])
        elif item.startswith(NOTE_PREFIX):
            notes.append(item[len(NOTE_PREFIX) :])
        else:
            failures.append(item)
    return failures, pending, notes


def run_checks(*, with_tests: bool = False) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for check_id, description, function in CHECKS:
        try:
            outcome = function(ROOT)
        except Exception as error:  # a check that cannot run is a failed check
            results.append(
                {
                    "check_id": check_id,
                    "description": description,
                    "status": FAIL,
                    "failures": [f"{type(error).__name__}: {error}"],
                    "pending": [],
                    "notes": [],
                }
            )
            continue
        failures, pending, notes = _triage(list(outcome))
        if failures:
            status = FAIL
        elif pending:
            status = PENDING
        else:
            status = PASS
        results.append(
            {
                "check_id": check_id,
                "description": description,
                "status": status,
                "failures": failures,
                "pending": pending,
                "notes": notes,
            }
        )

    if with_tests:
        status, evidence = _check_tests(ROOT)
        failures, pending, notes = _triage(list(evidence))
        results.append(
            {
                "check_id": "tests",
                "description": "Full pytest suite",
                "status": status,
                "failures": failures,
                "pending": [],
                "notes": pending + notes,
            }
        )
    else:
        results.append(
            {
                "check_id": "tests",
                "description": "Full pytest suite",
                "status": SKIP,
                "failures": [],
                "pending": [],
                "notes": ["not run: pass --with-tests (or use 'run test')"],
            }
        )

    failed = [item["check_id"] for item in results if item["status"] == FAIL]
    pending_checks = [item["check_id"] for item in results if item["status"] == PENDING]
    return {
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "root": ROOT.as_posix(),
        "with_tests": with_tests,
        "ok": not failed,
        "failed": failed,
        "pending": pending_checks,
        "checks": results,
    }


def render(report: dict[str, object]) -> str:
    markers = {PASS: "PASS", FAIL: "FAIL", SKIP: "SKIP", PENDING: "PENDING"}
    lines = [
        f"verification run: {'PASS' if report['ok'] else 'FAIL'}"
        + (f" ({len(report['pending'])} check(s) pending)" if report.get("pending") else ""),
        f"root: {report['root']}",
        f"python: {report['python']}",
        f"checked at: {report['checked_at']}",
        "",
    ]
    for item in report["checks"]:
        lines.append(f"[{markers[item['status']]}] {item['check_id']}: {item['description']}")
        for line in item["failures"]:
            lines.append(f"    FAIL  {line}")
        for line in item["pending"]:
            lines.append(f"    later {line}")
        for line in item["notes"]:
            lines.append(f"    note  {line}")
    lines.extend(
        [
            "",
            "'later' items are work this workspace has not started yet (contest not",
            "configured, no claims, no Gate approvals). They are reported, never hidden,",
            "and they do not mark the workspace as broken.",
            "",
            "note: this run proves the deterministic checks above. It is NOT an independent",
            "verification: reports/verify.json stays 'pending' until a human records an",
            "independent reviewer, and G7 still requires an explicit human decision.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic verification. Never records an independent verification "
            "and never approves a Human Gate."
        )
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--with-tests", action="store_true", help="Include the pytest suite.")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write {REPORT_PATH.relative_to(ROOT).as_posix()} (never reports/verify.json).",
    )
    args = parser.parse_args()

    report = run_checks(with_tests=args.with_tests)
    if args.write_report:
        # Only the schema's three statuses are allowed, so a pending check is
        # recorded as not_applicable with its reasons in `evidence`; the run's own
        # verdict lives under `run`.
        def _status(item: dict[str, object]) -> str:
            status = str(item["status"])
            return status if status in {"pass", "fail", "not_applicable"} else "not_applicable"

        payload = {
            "schema_version": "1.0",
            "status": "pending",
            "verified_at": None,
            "checks": [
                {
                    "check_id": item["check_id"],
                    "status": _status(item),
                    "evidence": [
                        *(f"FAIL: {value}" for value in item["failures"]),
                        *(f"LATER: {value}" for value in item["pending"]),
                        *(f"NOTE: {value}" for value in item["notes"]),
                    ],
                    "notes": item["description"],
                }
                for item in report["checks"]
            ],
            "notes": (
                "Deterministic verification run by scripts/verify.py. This is not an "
                "independent verification; reports/verify.json must be completed by an "
                "independent reviewer."
            ),
            "run": {
                "checked_at": report["checked_at"],
                "python": report["python"],
                "root": report["root"],
                "with_tests": report["with_tests"],
                "ok": report["ok"],
            },
        }
        dump_json(REPORT_PATH, payload)
        print(f"verification report: {REPORT_PATH.as_posix()}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
