from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, load_json, load_yaml, model_status, sha256_file, within_root
from scripts.auto_route import gate_inventory_errors

JSON_CONTRACTS = {
    "run-manifest.json": "90_工具与配置/schemas/run-manifest.schema.json",
    "03_建模工作区/results/results.json": "90_工具与配置/schemas/results.schema.json",
    "03_建模工作区/figures/manifest.json": "90_工具与配置/schemas/figure-manifest.schema.json",
    "04_论文与提交/references/references.json": "90_工具与配置/schemas/references.schema.json",
    "90_工具与配置/reports/verify.json": "90_工具与配置/schemas/verify.schema.json",
}


def _schema_errors(instance: Any, schema: Any) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{location}: {error.message}")
    return errors


def gate_violations(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    approved_statuses = {"approved", "complete", "passed"}
    for index, stage in enumerate(manifest.get("stages", [])):
        name = str(stage.get("name", ""))
        is_gate = (
            bool(re.match(r"^G\d+\b", name, flags=re.IGNORECASE))
            or stage.get("type") == "gate"
        )
        if not is_gate or str(stage.get("status", "")).lower() not in approved_statuses:
            continue
        approver = str(stage.get("approved_by", "")).strip()
        approved_at = stage.get("approved_at")
        if not approver or approver.lower() in {
            "ai",
            "agent",
            "codex",
            "orchestrator",
            "hook",
            "skill",
            "subagent",
        }:
            errors.append(f"stages/{index}: approved gate {name!r} lacks a human approved_by value")
        if not approved_at:
            errors.append(f"stages/{index}: approved gate {name!r} lacks approved_at")
    return errors


def frozen_model_violations(text: str) -> list[str]:
    errors: list[str] = []
    status = model_status(text)
    if status not in {"UNINITIALIZED", "DRAFT", "FROZEN"}:
        errors.append(f"MODEL_SPEC has invalid or missing Status: {status!r}")
        return errors
    if status == "FROZEN":
        approval_match = re.search(r"^Human approval:\s*(.+)$", text, flags=re.MULTILINE)
        approval = approval_match.group(1).strip().lower() if approval_match else ""
        if not approval or approval in {"not granted", "pending", "none"}:
            errors.append("FROZEN MODEL_SPEC lacks explicit human approval")
        for label in ("Approved by", "Approved at"):
            match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", text, flags=re.MULTILINE)
            value = match.group(1).strip().lower() if match else ""
            if not value or value in {"pending", "none", "ai", "codex", "orchestrator"}:
                errors.append(f"FROZEN MODEL_SPEC lacks valid human {label.lower()} metadata")
        freeze_match = re.search(r"^- Freeze state:\s*(.+)$", text, flags=re.MULTILINE)
        if not freeze_match or freeze_match.group(1).strip().lower() != "frozen":
            errors.append("FROZEN MODEL_SPEC must record '- Freeze state: frozen'")
    return errors


def artifact_run_link_errors(
    *, label: str, run_id: str, artifact: Path, declared_sha256: str | None,
    run_records: dict[str, dict[str, Any]], root: Path,
) -> list[str]:
    """Prove that a registered artifact is byte-identical to one run output."""
    errors: list[str] = []
    run = run_records.get(run_id)
    if run is None:
        return [f"{label}: unknown run_id {run_id}"]
    if not within_root(artifact, root) or not artifact.is_file():
        return [f"{label}: missing or unsafe artifact {artifact}"]
    actual = sha256_file(artifact)
    if declared_sha256 is not None and actual != declared_sha256:
        errors.append(f"{label}: artifact_sha256 does not match file")
    output_hashes = {item.get("sha256") for item in run.get("outputs", [])}
    if actual not in output_hashes:
        errors.append(f"{label}: artifact is not a hashed output of run_id {run_id}")
    return errors


def validate_project(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    loaded: dict[str, Any] = {}
    for artifact, schema_path in JSON_CONTRACTS.items():
        try:
            instance = load_json(root / artifact)
            schema = load_json(root / schema_path)
            loaded[artifact] = instance
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{artifact}: cannot load contract: {exc}")
            continue
        errors.extend(f"{artifact}: {item}" for item in _schema_errors(instance, schema))

    try:
        evidence = load_yaml(root / "03_建模工作区" / "evidence" / "EVIDENCE_PASSPORT.yaml")
        evidence_schema = load_json(
            root / "90_工具与配置" / "schemas" / "evidence-passport.schema.json"
        )
        errors.extend(
            f"evidence/EVIDENCE_PASSPORT.yaml: {item}"
            for item in _schema_errors(evidence, evidence_schema)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"evidence/EVIDENCE_PASSPORT.yaml: cannot load contract: {exc}")

    registry_path = root / "03_建模工作区" / "experiments" / "registry.csv"
    experiment_ids: set[str] = set()
    try:
        experiment_schema = load_json(
            root / "90_工具与配置" / "schemas" / "experiment-record.schema.json"
        )
        with registry_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            expected = list(experiment_schema["required"])
            if reader.fieldnames != expected:
                errors.append(
                    "experiments/registry.csv: header mismatch; expected " + ",".join(expected)
                )
            for row_number, row in enumerate(reader, start=2):
                row_errors = _schema_errors(row, experiment_schema)
                errors.extend(
                    f"experiments/registry.csv:{row_number}: {item}" for item in row_errors
                )
                experiment_id = row.get("experiment_id", "")
                if experiment_id in experiment_ids:
                    errors.append(
                        f"experiments/registry.csv:{row_number}: duplicate "
                        f"experiment_id {experiment_id}"
                    )
                experiment_ids.add(experiment_id)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"experiments/registry.csv: cannot validate: {exc}")

    manifest = loaded.get("run-manifest.json", {})
    from scripts.artifact_state import invalidate
    errors.extend(
        f"run-manifest.json: stale PASS: {item}"
        for item in invalidate(root / "90_工具与配置/state/artifact_snapshots.json", root=root)
    )
    errors.extend(f"run-manifest.json: {item}" for item in gate_inventory_errors(manifest))
    errors.extend(f"run-manifest.json: {item}" for item in gate_violations(manifest))
    approved = set(manifest.get("approved_artifacts", []))
    stale = set(manifest.get("stale_artifacts", []))
    for relative in approved:
        if not (root / relative).exists():
            errors.append(f"run-manifest.json: approved artifact does not exist: {relative}")
    overlap = approved & stale
    if overlap:
        errors.append(
            "run-manifest.json: artifacts cannot be both approved and stale: "
            + ", ".join(sorted(overlap))
        )

    model_path = root / "03_建模工作区" / "model" / "MODEL_SPEC.md"
    try:
        errors.extend(
            f"model/MODEL_SPEC.md: {item}"
            for item in frozen_model_violations(model_path.read_text(encoding="utf-8"))
        )
    except OSError as exc:
        errors.append(f"model/MODEL_SPEC.md: cannot read: {exc}")

    runs_root = root / "03_建模工作区" / "runs"
    from scripts.run_record import validate_run_record
    run_records: dict[str, dict[str, Any]] = {}
    for run_path in sorted(runs_root.glob("*/manifest.json")):
        try:
            record = load_json(run_path)
            run_records[record.get("run_id", run_path.parent.name)] = record
            errors.extend(f"runs/{run_path.parent.name}: {item}" for item in
                          validate_run_record(record, run_path.parent, root=root))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"runs/{run_path.parent.name}: invalid manifest: {exc}")

    results_key = "03_建模工作区/results/results.json"
    results = loaded.get(results_key, {}).get("results", [])
    if results and not loaded[results_key].get("generated_at"):
        errors.append("results/results.json: non-empty registry lacks generated_at")
    result_ids: set[str] = set()
    for index, result in enumerate(results):
        result_id = result["result_id"]
        if result_id in result_ids:
            errors.append(f"results/results.json: duplicate result_id {result_id}")
        result_ids.add(result_id)
        if result["experiment_id"] not in experiment_ids:
            errors.append(
                f"results/results.json:{index}: unknown experiment_id {result['experiment_id']}"
            )
        errors.extend(artifact_run_link_errors(
            label=f"results/results.json:{index}",
            run_id=result["run_id"],
            artifact=root / result["artifact_path"],
            declared_sha256=result["artifact_sha256"],
            run_records=run_records,
            root=root,
        ))

    figures_key = "03_建模工作区/figures/manifest.json"
    figures = loaded.get(figures_key, {}).get("figures", [])
    figure_ids: set[str] = set()
    for index, figure in enumerate(figures):
        figure_id = figure["figure_id"]
        if figure_id in figure_ids:
            errors.append(f"figures/manifest.json: duplicate figure_id {figure_id}")
        figure_ids.add(figure_id)
        if figure.get("result_source") and figure["result_source"] not in result_ids:
            errors.append(
                f"figures/manifest.json:{index}: unknown result_source {figure['result_source']}"
            )
        run = run_records.get(figure["run_id"])
        if run is None:
            errors.append(f"figures/manifest.json:{index}: unknown run_id {figure['run_id']}")
        elif figure["script"] not in run.get("code_hashes", {}):
            errors.append(
                f"figures/manifest.json:{index}: rendering script is not bound in run code_hashes"
            )
        for key in ("script", "figure_contract", "output_png"):
            artifact = root / figure[key]
            if not within_root(artifact, root) or not artifact.is_file():
                errors.append(
                    f"figures/manifest.json:{index}: missing or unsafe {key}: {figure[key]}"
                )
        for key in ("output_png", "output_svg", "output_pdf"):
            if figure.get(key):
                errors.extend(artifact_run_link_errors(
                    label=f"figures/manifest.json:{index}/{key}",
                    run_id=figure["run_id"],
                    artifact=root / figure[key],
                    declared_sha256=None,
                    run_records=run_records,
                    root=root,
                ))
        if not figure.get("output_svg") and not figure.get("output_pdf"):
            errors.append(
                f"figures/manifest.json:{index}: formal figure lacks SVG or PDF vector output"
            )

    verify_key = "90_工具与配置/reports/verify.json"
    verify_path = root / verify_key
    try:
        verification = loaded.get(verify_key, load_json(verify_path))
        if verification.get("status") == "verified":
            if not verification.get("verified_at"):
                errors.append("reports/verify.json: verified status lacks verified_at")
            if not verification.get("independent_reviewer"):
                errors.append("reports/verify.json: verified status lacks independent_reviewer")
            if not verification.get("checks"):
                errors.append("reports/verify.json: verified status lacks checks")
            if any(check.get("status") != "pass" for check in verification.get("checks", [])):
                errors.append("reports/verify.json: verified status contains a non-pass check")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"reports/verify.json: cannot load: {exc}")

    # Calculation -> run manifest -> claim is checked when these optional registries exist.
    claim_path = root / "04_论文与提交" / "paper" / "claim_registry.jsonl"
    if claim_path.exists():
        from scripts.claim_registry import check_registry
        errors.extend(f"claim_registry: {item}" for item in
                      check_registry(claim_path, runs_root=runs_root, root=root))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical project contracts.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = validate_project()
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print("contracts: FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print("contracts: PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
