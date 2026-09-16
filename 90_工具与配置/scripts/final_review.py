#!/usr/bin/env python3
"""Record an independent human review of the project's final verification.

This is deliberately a *narrow* tool.  It exists so that
``90_工具与配置/reports/verify.json`` can be completed by a named independent
reviewer without anyone hand-editing JSON - and so that nothing else can.

What it will never do:

* it does not read a machine ``verify`` run and turn its result into an
  independent verification;
* it does not invent, default, or infer the reviewer, the timestamp, or any
  check status;
* it cannot be run without a human identity and a note;
* it does not approve G7, write ``run-manifest.json``, or touch a Gate record.

The deterministic chain lives in ``scripts/verify.py``.  That command proves the
checks; this command only records that *a person* accepted or rejected the
result, together with the evidence they relied on.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, TOOLS_ROOT, load_json

REPORT_PATH = TOOLS_ROOT / "reports" / "verify.json"
SCHEMA_PATH = TOOLS_ROOT / "schemas" / "verify.schema.json"
CONTEST_CONFIG = TOOLS_ROOT / "configs" / "contest.yaml"
MANIFEST_PATH = ROOT / "run-manifest.json"

STATUSES = ("pass", "fail", "not_applicable")
AI_IDENTITIES = {
    "ai", "agent", "codex", "chatgpt", "llm", "model", "orchestrator",
    "hook", "skill", "subagent", "bot", "assistant", "openai",
}


class ReviewError(RuntimeError):
    """A condition the reviewer must fix; always reported without a traceback."""


def validate_reviewer(value: str) -> str:
    """Reject automation identities: an independent review is a human act."""
    reviewer = value.strip()
    tokens = set(re.findall(r"[a-z0-9]+", reviewer.casefold()))
    if not reviewer:
        raise ReviewError("--reviewer is required")
    if tokens & AI_IDENTITIES:
        raise ReviewError(
            "--reviewer must identify a human being, not an AI or an automated process"
        )
    if len(reviewer) < 2:
        raise ReviewError("--reviewer is too short to identify a person")
    return reviewer


def parse_check(value: str) -> dict[str, object]:
    """Parse ``status: check_id: evidence`` (evidence optional)."""
    status, separator, remainder = value.partition(":")
    if not separator:
        raise ReviewError(
            f"cannot read check {value!r}; expected 'status: check_id: evidence'"
        )
    status = status.strip().lower()
    if status not in STATUSES:
        raise ReviewError(f"unknown check status {status!r}; expected one of {', '.join(STATUSES)}")
    check_id, _, evidence = remainder.partition(":")
    check_id = check_id.strip()
    if not check_id:
        raise ReviewError(f"check {value!r} has no check_id")
    return {
        "check_id": check_id,
        "status": status,
        "evidence": [evidence.strip()] if evidence.strip() else [],
        "notes": "",
    }


PENDING_TEMPLATE = """{
  "$schema": "../schemas/verify.schema.json",
  "schema_version": "1.0",
  "status": "pending",
  "verified_at": null,
  "checks": [],
  "notes": "Independent final verification has not been performed for a contest submission."
}
"""


def pending_report() -> dict[str, object]:
    return {
        "$schema": "../schemas/verify.schema.json",
        "schema_version": "1.0",
        "status": "pending",
        "verified_at": None,
        "checks": [],
        "notes": "Independent final verification has not been performed for a contest submission.",
    }


def project_newline() -> str:
    """The project's own line-ending convention, so writes match the checkout.

    Deriving it from a stable, tracked reference file - not from the artifact
    being rewritten - keeps `record` and `reset` consistent with each other even
    after several round trips.  A Windows checkout normalised by git uses CRLF;
    a Linux checkout uses LF.  CI on Windows caught the mismatch.
    """
    references = [ROOT / "pyproject.toml"]
    schemas = sorted((TOOLS_ROOT / "schemas").glob("*.schema.json"))
    if schemas:
        references.append(schemas[0])
    references.append(TOOLS_ROOT / "configs" / "workspace-layout.yaml")
    for path in references:
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\r\n" in data:
            return "\r\n"
        if b"\n" in data:
            return "\n"
    return "\n"


def _write_report_text(text: str) -> None:
    """Write the report with the project's newline style, byte for byte."""
    newline = project_newline()
    payload = text if newline == "\n" else text.replace("\n", newline)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_bytes(payload.encode("utf-8"))


def load_report() -> dict[str, object]:
    if not REPORT_PATH.is_file():
        return pending_report()
    try:
        report = load_json(REPORT_PATH)
    except (OSError, ValueError) as error:
        raise ReviewError(f"cannot read {REPORT_PATH.as_posix()}: {error}") from error
    if not isinstance(report, dict):
        raise ReviewError(f"{REPORT_PATH.as_posix()} must contain a JSON object")
    return report


def schema_errors(report: dict[str, object]) -> list[str]:
    if not SCHEMA_PATH.is_file():
        return []
    from jsonschema import Draft202012Validator, FormatChecker

    validator = Draft202012Validator(load_json(SCHEMA_PATH), format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(report)]


def gate7_dependencies() -> dict[str, object]:
    """The G7 preconditions a reviewer is being asked to accept.

    Reported for information only.  Recording a verification does not approve G7,
    so these are surfaced so the reviewer can see what remains outstanding.
    """
    facts: dict[str, object] = {}
    facts["verify_report_status"] = load_report().get("status")
    facts["g7_approved"] = False
    if MANIFEST_PATH.is_file():
        try:
            from scripts.auto_route import valid_human_gate

            manifest = load_json(MANIFEST_PATH)
            facts["g7_approved"] = valid_human_gate(manifest, "G7")
        except (OSError, ValueError) as error:
            facts["manifest_error"] = str(error)
    if CONTEST_CONFIG.is_file():
        try:
            from scripts._project import load_yaml

            contest = load_yaml(CONTEST_CONFIG)
            if isinstance(contest, dict):
                facts["contest"] = contest.get("contest")
                facts["control_number_set"] = bool(contest.get("control_number"))
                facts["paper_pdf_set"] = bool(contest.get("paper_pdf"))
        except (OSError, ValueError) as error:
            facts["contest_config_error"] = str(error)
    return facts


def record(
    *,
    reviewer: str,
    note: str,
    checks: list[dict[str, object]],
    accept: bool,
) -> dict[str, object]:
    reviewer = validate_reviewer(reviewer)
    note = note.strip()
    if not note:
        raise ReviewError("--note is required: say what you reviewed and why you accepted it")
    if not checks:
        raise ReviewError(
            "at least one --check is required; record what you actually inspected"
        )
    report = {
        "$schema": "../schemas/verify.schema.json",
        "schema_version": "1.0",
        "status": "verified" if accept else "rejected",
        "verified_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "independent_reviewer": reviewer,
        "checks": checks,
        "notes": note,
    }
    errors = schema_errors(report)
    if errors:
        raise ReviewError("recorded verification is invalid: " + "; ".join(errors))
    if any(check["status"] != "pass" for check in checks) and accept:
        raise ReviewError(
            "cannot record 'verified' while a check is not 'pass'; use --reject instead"
        )
    _write_report_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def reset() -> dict[str, object]:
    """Return the report to its shipped pending state, byte for byte.

    The pending report is written with the project's newline style, so on a
    Windows checkout normalised to CRLF the reset restores the file exactly
    instead of leaving a spurious diff.  (CI caught this: Linux passed, Windows
    did not.)
    """
    _write_report_text(PENDING_TEMPLATE)
    return pending_report()


def render(report: dict[str, object], facts: dict[str, object]) -> str:
    lines = [
        f"verification report: {REPORT_PATH.relative_to(ROOT).as_posix()}",
        f"  status            : {report.get('status')}",
        f"  verified_at       : {report.get('verified_at')}",
        f"  reviewer          : {report.get('independent_reviewer', '(none)')}",
        f"  checks            : {len(report.get('checks', []))}",
        f"  notes             : {report.get('notes')}",
        "",
        "G7 preconditions (not changed by this command):",
        f"  G7 human approval : {facts.get('g7_approved')}",
        f"  contest configured: {facts.get('contest')}",
        f"  control number    : {facts.get('control_number_set')}",
        f"  submission pdf    : {facts.get('paper_pdf_set')}",
        "",
        "Recording a verification does NOT approve G7. A release to submit still needs",
        "an explicit human G7 decision, and this command never writes a Gate record.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record an independent human review of the final verification. Never infers a "
            "reviewer, never upgrades a machine verify run, never approves G7."
        )
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("show", help="Show the current verification report and G7 preconditions.")
    sub.add_parser("reset", help="Return the report to 'pending' (removes the review record).")

    record_parser = sub.add_parser("record", help="Record a human review decision.")
    record_parser.add_argument("--reviewer", required=True, help="Name of the independent human reviewer.")
    record_parser.add_argument("--note", required=True, help="What was reviewed and why.")
    record_parser.add_argument(
        "--check",
        action="append",
        default=[],
        metavar="STATUS:CHECK_ID[:EVIDENCE]",
        help="Repeatable. STATUS is pass, fail or not_applicable.",
    )
    verdict = record_parser.add_mutually_exclusive_group()
    verdict.add_argument("--accept", action="store_true", help="Record status 'verified'.")
    verdict.add_argument("--reject", action="store_true", help="Record status 'rejected'.")

    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    try:
        if args.command == "reset":
            report = reset()
            print(f"verification report reset to 'pending': {REPORT_PATH.as_posix()}")
        elif args.command == "record":
            checks = [parse_check(value) for value in args.check]
            report = record(
                reviewer=args.reviewer,
                note=args.note,
                checks=checks,
                accept=not args.reject,
            )
            print(
                f"verification report: {report['status']} by {report['independent_reviewer']} "
                f"at {report['verified_at']}"
            )
        else:
            report = load_report()
    except ReviewError as error:
        print(f"final-review: FAIL\n  {error}", file=sys.stderr)
        return 2

    facts = gate7_dependencies()
    if args.json:
        print(json.dumps({"report": report, "g7_preconditions": facts}, ensure_ascii=False, indent=2))
    else:
        print(render(report, facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
