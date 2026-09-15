from __future__ import annotations

import argparse
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
from scripts.auto_route import valid_human_gate
from scripts.compliance import collect_findings
from scripts.validate_contracts import validate_project
from scripts.package_guard import assert_package_files
from scripts.artifact_state import invalidate_manifest


def readiness_blockers(root: Path = ROOT) -> list[str]:
    blockers = [f"contract: {error}" for error in validate_project(root)]
    manifest = load_json(root / "run-manifest.json")
    invalidate_manifest(
        manifest, path=root / "90_工具与配置/state/artifact_snapshots.json", root=root
    )
    if not valid_human_gate(manifest, "G7"):
        blockers.append("G7 ready-to-submit lacks explicit human approval")
    blockers.extend(
        f"{finding['code']}: {finding['message']}"
        for finding in collect_findings(root, submission=True)
        if finding["level"] == "BLOCKER"
    )
    tools = TOOLS_ROOT if root == ROOT else tools_root(root)
    verification = load_json(tools / "reports" / "verify.json")
    if verification.get("status") != "verified":
        blockers.append("90_工具与配置/reports/verify.json is not independently verified")
    try:
        package_files(root)
    except (ValueError, OSError) as error:
        blockers.append(f"package boundary: {error}")
    return list(dict.fromkeys(blockers))


def package_files(root: Path = ROOT) -> list[Path]:
    tools = TOOLS_ROOT if root == ROOT else tools_root(root)
    work = WORK_ROOT if root == ROOT else work_root(root)
    papers = PAPER_ROOT if root == ROOT else paper_root(root)
    config = load_yaml(tools / "configs" / "contest.yaml")
    paper = root / str(config["paper_pdf"])
    candidates = [
        paper,
        work / "results" / "results.json",
        work / "figures" / "manifest.json",
        papers / "references" / "references.json",
        papers / "ai_provenance" / "AI_USAGE_SUBMISSION.md",
    ]
    candidates.extend(path for path in (work / "src").rglob("*") if path.is_file())
    candidates.extend(path for path in (work / "figures" / "final").rglob("*") if path.is_file())
    selected = {path for path in candidates if path.is_file()}
    assert_package_files(selected, root)
    return sorted(
        selected,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def build_archive(output: Path, root: Path = ROOT) -> None:
    if not within_root(output, root):
        raise ValueError("submission output must stay inside the workspace")
    manifest_path = root / "run-manifest.json"
    if not manifest_path.is_file() or not valid_human_gate(load_json(manifest_path), "G7"):
        raise PermissionError("G7 ready-to-submit requires explicit human approval")
    blockers = readiness_blockers(root)
    if blockers:
        raise PermissionError("; ".join(blockers))
    sources = package_files(root)
    assert_package_files(sources, root)
    assert_package_files([output], root)
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
        return 1
    if args.build:
        build_archive(args.output.resolve())
        print(f"submission package: {args.output.resolve()}")
    else:
        print("submission readiness: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
