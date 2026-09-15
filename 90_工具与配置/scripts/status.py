from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import (
    ROOT,
    WORK_ROOT,
    iter_input_files,
    iter_literature_files,
    load_json,
    load_yaml,
    model_status,
    requirement_files,
    work_root,
)


def collect_status(root: Path = ROOT) -> dict[str, object]:
    manifest = load_json(root / "run-manifest.json")
    work = WORK_ROOT if root == ROOT else work_root(root)
    with (work / "experiments" / "registry.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        experiment_count = sum(1 for _ in csv.DictReader(handle))
    return {
        "project_id": manifest["project_id"],
        "contest": manifest["contest"],
        "status": manifest["status"],
        "stages": manifest["stages"],
        "model_status": model_status(
            (work / "model" / "MODEL_SPEC.md").read_text(encoding="utf-8")
        ),
        "input_files": len(iter_input_files(root)),
        "literature_files": len(iter_literature_files(root)),
        "requirement_files": len(requirement_files(root)),
        "evidence_records": len(
            load_yaml(work / "evidence" / "EVIDENCE_PASSPORT.yaml").get("records", [])
        ),
        "experiments": experiment_count,
        "formal_results": len(load_json(work / "results" / "results.json")["results"]),
        "formal_figures": len(load_json(work / "figures" / "manifest.json")["figures"]),
        "approved_artifacts": manifest["approved_artifacts"],
        "stale_artifacts": manifest["stale_artifacts"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Show canonical workflow state.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    status = collect_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"project: {status['project_id']}")
        print(f"contest: {status['contest']}")
        print(f"workflow status: {status['status']}")
        print(f"model status: {status['model_status']}")
        print(
            "records: "
            f"evidence={status['evidence_records']}, experiments={status['experiments']}, "
            f"results={status['formal_results']}, figures={status['formal_figures']}"
        )
        for stage in status["stages"]:
            print(f"stage {stage['name']}: {stage['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
