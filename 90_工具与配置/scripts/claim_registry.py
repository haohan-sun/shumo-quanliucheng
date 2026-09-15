"""Claim registry: every load-bearing paper claim traces to evidence.

Registry: 04_论文与提交/paper/claim_registry.jsonl
A claim without supporting run_ids/figures/tables/sources is INVALID for writing.

CLI:
    python .../claim_registry.py --check            # validate whole registry
    python .../claim_registry.py --orphans paper.md # find unsupported numeric claims
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import PAPER_ROOT, ROOT, WORK_ROOT

REGISTRY_PATH = PAPER_ROOT / "paper" / "claim_registry.jsonl"
CLAIM_TYPES = ("result", "comparison", "robustness", "novelty", "answer")
STATUSES = ("draft", "verified", "retracted")


def add_claim(
    paper_section: str,
    claim: str,
    claim_type: str,
    *,
    supporting_run_ids: list[str] | None = None,
    supporting_figures: list[str] | None = None,
    supporting_tables: list[str] | None = None,
    supporting_sources: list[str] | None = None,
    confidence: str = "medium",
    path: Path = REGISTRY_PATH,
) -> dict:
    if claim_type not in CLAIM_TYPES:
        raise ValueError(f"claim_type must be one of {CLAIM_TYPES}")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("confidence must be low/medium/high")
    entry = {
        "claim_id": f"C{uuid.uuid4().hex[:8]}",
        "paper_section": paper_section,
        "claim": claim,
        "type": claim_type,
        "supporting_run_ids": list(supporting_run_ids or []),
        "supporting_figures": list(supporting_figures or []),
        "supporting_tables": list(supporting_tables or []),
        "supporting_sources": list(supporting_sources or []),
        "confidence": confidence,
        "status": "draft",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _has_evidence(entry: dict) -> bool:
    return bool(
        entry.get("supporting_run_ids")
        or entry.get("supporting_figures")
        or entry.get("supporting_tables")
        or entry.get("supporting_sources")
    )


def _computational_run_errors(run: dict, *, require_clean: bool) -> list[str]:
    """Reject bookkeeping-only records as evidence for computational claims."""
    errors: list[str] = []
    if not run.get("git_commit"):
        errors.append("run has no git commit")
    if not run.get("code_hashes"):
        errors.append("run has no hashed code")
    if not run.get("outputs"):
        errors.append("run has no hashed outputs")
    if run.get("runtime_seconds") is None:
        errors.append("run has no measured runtime")
    metrics = run.get("metrics", {})
    if metrics.get("exit_code") != 0 or metrics.get("timed_out") is not False:
        errors.append("run lacks a successful tracked execution record")
    if require_clean and run.get("git_dirty") is not False:
        errors.append("verified claim cannot depend on a dirty working-tree run")
    return errors


def check_registry(path: Path = REGISTRY_PATH, *, runs_root: Path | None = None,
                   root: Path = ROOT) -> list[str]:
    """Blocking errors = claim without evidence, unknown status, or dangling run_ids."""
    errors: list[str] = []
    if not path.is_file():
        return ["claim registry missing (create it before paper writing)"]
    runs_root = Path(runs_root) if runs_root is not None else root / "03_建模工作区/runs"
    known_runs = {m.parent.name: m for m in runs_root.glob("*/manifest.json")}
    seen: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("claim must be an object")
        except (ValueError, TypeError) as exc:
            errors.append(f"line{line_no}: invalid JSON claim: {exc}")
            continue
        claim_id = entry.get("claim_id", f"line{line_no}")
        if claim_id in seen:
            errors.append(f"{claim_id}: duplicate claim_id")
        seen.add(claim_id)
        if entry.get("type") not in CLAIM_TYPES:
            errors.append(f"{claim_id}: unknown type {entry.get('type')!r}")
        if entry.get("status") not in STATUSES:
            errors.append(f"{claim_id}: unknown status {entry.get('status')!r}")
        if entry.get("status") != "retracted" and not _has_evidence(entry):
            errors.append(f"{claim_id}: load-bearing claim without any supporting evidence")
        if (entry.get("status") != "retracted"
                and entry.get("type") in {"result", "comparison", "robustness", "answer"}
                and not entry.get("supporting_run_ids")):
            errors.append(f"{claim_id}: computational claim requires a supporting run_id")
        if entry.get("status") != "retracted":
            for run_id in entry.get("supporting_run_ids", []):
                if run_id not in known_runs:
                    errors.append(f"{claim_id}: supporting run_id {run_id} has no run record")
                else:
                    from scripts.run_record import validate_run_record
                    manifest = known_runs[run_id]
                    try:
                        run = json.loads(manifest.read_text(encoding="utf-8"))
                        errors.extend(f"{claim_id}: {run_id}: {error}" for error in
                                      validate_run_record(run, manifest.parent, root=root))
                        if entry.get("type") in {"result", "comparison", "robustness", "answer"}:
                            errors.extend(
                                f"{claim_id}: {run_id}: {error}"
                                for error in _computational_run_errors(
                                    run, require_clean=entry.get("status") == "verified"
                                )
                            )
                    except (ValueError, OSError) as exc:
                        errors.append(f"{claim_id}: invalid run record: {exc}")
            from scripts.artifact_state import resolve_artifact
            for category in ("supporting_figures", "supporting_tables", "supporting_sources"):
                for dep in entry.get(category, []):
                    # External source identifiers are checked by literature integrity, not fetched here.
                    if category == "supporting_sources" and dep.startswith(("https://", "doi:")):
                        continue
                    try:
                        if not resolve_artifact(dep, root).is_file():
                            errors.append(f"{claim_id}: missing evidence {dep}")
                    except ValueError as exc:
                        errors.append(f"{claim_id}: {exc}")
    return errors


_NUMERIC = re.compile(r"\d+(?:\.\d+)?(?:%|[eE][+-]?\d+)?")


def orphan_numeric_claims(paper_path: Path, registry_path: Path = REGISTRY_PATH) -> list[str]:
    """Sentences in the paper containing numbers but not covered by any claim text overlap.

    Heuristic guard: lists sentence numbers that the writer must either register
    as claims or justify as non-load-bearing (definitions, section numbers...).
    """
    claims = []
    if registry_path.is_file():
        claims = [json.loads(l)["claim"] for l in registry_path.read_text(encoding="utf-8").splitlines()]
    orphans: list[str] = []
    for line_no, line in enumerate(Path(paper_path).read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "%", "\\,", "|", "!", "[")):
            continue
        for match in _NUMERIC.findall(stripped):
            if not any(match in claim for claim in claims):
                orphans.append(f"line {line_no}: number {match} not covered by any registered claim")
                break
    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim registry check.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--orphans", type=Path, metavar="PAPER")
    args = parser.parse_args()
    if args.check:
        errors = check_registry(REGISTRY_PATH, runs_root=WORK_ROOT / "runs")
        print("\n".join(errors) if errors else "claim registry: PASS")
        return 1 if errors else 0
    if args.orphans:
        orphans = orphan_numeric_claims(args.orphans)
        print("\n".join(orphans) if orphans else "no orphan numeric claims found")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
