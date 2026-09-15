from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, dump_json, input_hashes, load_json


def update_manifest(root: Path = ROOT) -> tuple[dict[str, str], bool]:
    path = root / "run-manifest.json"
    manifest = load_json(path)
    hashes = input_hashes(root)
    changed = manifest.get("input_hashes", {}) != hashes
    if changed:
        approved = set(manifest.get("approved_artifacts", []))
        stale = set(manifest.get("stale_artifacts", []))
        manifest["stale_artifacts"] = sorted(stale | approved)
        manifest["input_hashes"] = hashes
        dump_json(path, manifest)
    return hashes, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash official problem and raw-data inputs.")
    parser.add_argument("--update", action="store_true", help="Update run-manifest.json.")
    args = parser.parse_args()
    if args.update:
        hashes, changed = update_manifest()
    else:
        hashes, changed = input_hashes(), False
    print(
        json.dumps(
            {"input_hashes": hashes, "manifest_updated": changed},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
