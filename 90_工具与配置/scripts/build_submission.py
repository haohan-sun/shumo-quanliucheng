from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import (
    PAPER_ROOT,
    ROOT,
    TOOLS_ROOT,
    WORK_ROOT,
    load_json,
    load_yaml,
    paper_root,
    tools_root,
    within_root,
    work_root,
)
from scripts.artifact_state import invalidate_manifest
from scripts.auto_route import valid_human_gate
from scripts.compliance import collect_findings
from scripts.package_guard import assert_package_files
from scripts.validate_contracts import validate_project

VERIFY_REPORT = "90_工具与配置/reports/verify.json"
CONTEST_CONFIG = "90_工具与配置/configs/contest.yaml"
PRUNED_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"})


def _load_optional(path: Path, loader, label: str) -> tuple[object | None, str | None]:
    """Load a configuration file, returning (value, blocker) instead of raising.

    A missing or malformed configuration is a readiness blocker the caller can
    report, not a traceback: ``package`` on a fresh clone must explain what is
    missing instead of crashing.
    """
    if not path.is_file():
        return None, f"{label} is missing: {path.as_posix()}"
    try:
        return loader(path), None
    except (OSError, ValueError, KeyError) as error:
        return None, f"{label} cannot be read: {type(error).__name__}: {error}"


def readiness_blockers(root: Path = ROOT) -> list[str]:
    blockers: list[str] = []
    try:
        blockers.extend(f"contract: {error}" for error in validate_project(root))
    except (OSError, ValueError) as error:
        blockers.append(f"contract: validation could not run: {type(error).__name__}: {error}")

    manifest, manifest_error = _load_optional(
        root / "run-manifest.json", load_json, "run-manifest.json"
    )
    if manifest_error:
        blockers.append(manifest_error)
    else:
        invalidate_manifest(
            manifest, path=root / "90_工具与配置/state/artifact_snapshots.json", root=root
        )
        if not valid_human_gate(manifest, "G7"):
            blockers.append("G7 ready-to-submit lacks explicit human approval")

    try:
        blockers.extend(
            f"{finding['code']}: {finding['message']}"
            for finding in collect_findings(root, submission=True)
            if finding["level"] == "BLOCKER"
        )
    except (OSError, ValueError) as error:
        blockers.append(f"compliance: checks could not run: {type(error).__name__}: {error}")

    tools = TOOLS_ROOT if root == ROOT else tools_root(root)
    verification, verify_error = _load_optional(
        tools / "reports" / "verify.json", load_json, "independent verification record"
    )
    if verify_error:
        blockers.append(verify_error)
    elif not isinstance(verification, dict) or verification.get("status") != "verified":
        blockers.append(f"{VERIFY_REPORT} is not independently verified")

    try:
        package_files(root)
    except (ValueError, OSError, KeyError) as error:
        blockers.append(f"package boundary: {error}")
    return list(dict.fromkeys(blockers))


def package_files(root: Path = ROOT) -> list[Path]:
    tools = TOOLS_ROOT if root == ROOT else tools_root(root)
    work = WORK_ROOT if root == ROOT else work_root(root)
    papers = PAPER_ROOT if root == ROOT else paper_root(root)
    config = load_yaml(tools / "configs" / "contest.yaml")
    if not isinstance(config, dict):
        raise ValueError(f"{CONTEST_CONFIG} must contain a mapping")
    paper = root / str(config["paper_pdf"]) if config.get("paper_pdf") else None
    candidates = [
        work / "results" / "results.json",
        work / "figures" / "manifest.json",
        papers / "references" / "references.json",
        papers / "ai_provenance" / "AI_USAGE_SUBMISSION.md",
    ]
    if paper is not None:
        candidates.insert(0, paper)
    candidates.extend(
        path
        for base in (work / "src", work / "figures" / "final")
        for path in _walk_deliverables(base)
    )
    selected = {path for path in candidates if path.is_file()}
    assert_package_files(selected, root)
    return sorted(
        selected,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _walk_deliverables(base: Path) -> list[Path]:
    """Files under ``base``, skipping regenerable interpreter caches.

    A plain ``rglob`` picks up ``__pycache__`` created by running the test suite,
    which the package boundary correctly refuses; pruning them during collection
    keeps the guard meaning "forbidden content", not "you ran the tests".
    """
    if not base.is_dir():
        return []
    found: list[Path] = []
    for directory, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [name for name in dirs if name not in PRUNED_CACHE_DIRS]
        found.extend(Path(directory) / name for name in files)
    return found


def build_archive(output: Path, root: Path = ROOT) -> None:
    if not within_root(output, root):
        raise ValueError("submission output must stay inside the workspace")
    manifest_path = root / "run-manifest.json"
    manifest, manifest_error = _load_optional(manifest_path, load_json, "run-manifest.json")
    if manifest_error or not valid_human_gate(manifest, "G7"):
        raise PermissionError("G7 ready-to-submit requires explicit human approval")
    blockers = readiness_blockers(root)
    if blockers:
        raise PermissionError("; ".join(blockers))
    sources = package_files(root)
    assert_package_files(sources, root)
    assert_package_files([output], root)
    if output.exists():
        raise FileExistsError(
            f"submission archive already exists: {output.as_posix()}\n"
            "Remove it or pass --output with a new path; existing deliverables are never overwritten."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, path.relative_to(root).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or build a verified submission package.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=PAPER_ROOT / "submission" / "modeling-submission.zip",
    )
    args = parser.parse_args()
    blockers = readiness_blockers()
    if blockers:
        print("submission readiness: BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        print(
            "note: BLOCKED is the expected result until a human records G7 and the "
            "independent verification record is complete."
        )
        return 1
    if args.build:
        try:
            build_archive(args.output.resolve())
        except (PermissionError, ValueError, OSError) as error:
            print("submission readiness: BLOCKED")
            print(f"- {error}")
            return 1
        print(f"submission package: {args.output.resolve()}")
    else:
        print("submission readiness: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
