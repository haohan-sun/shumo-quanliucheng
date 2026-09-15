"""Run record builder: one reproducible run = one directory under 03_建模工作区/runs/.

Usage (library):
    from scripts.run_record import create_run, finalize_run
    run = create_run(config={...}, seeds={"main": 42}, command=["python", "train.py"])
    ... execute, write outputs under run["dir"] ...
    finalize_run(run, metrics={"rmse": 0.31}, outputs=[("metrics.json", "metrics")])

CLI:
    python 90_工具与配置/scripts/run_record.py --list
    python 90_工具与配置/scripts/run_record.py --show <run_id>
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import uuid
import hashlib
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, WORK_ROOT, sha256_file

RUNS_ROOT = WORK_ROOT / "runs"
TRACKED_DEPS = ("numpy", "scipy", "pandas", "matplotlib", "scikit-learn", "statsmodels")
SPEC_PATH = WORK_ROOT / "model" / "MODEL_SPEC.md"


def _git_state() -> tuple[str | None, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, True


def _dep_versions() -> dict[str, str]:
    from importlib import metadata

    versions: dict[str, str] = {}
    for name in TRACKED_DEPS:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return versions


def _spec_version() -> str:
    if SPEC_PATH.is_file():
        import hashlib

        return hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()[:12]
    return "none"


def create_run(
    config: dict[str, Any],
    seeds: dict[str, int],
    command: list[str],
    parent_run: str | None = None,
    runs_root: Path = RUNS_ROOT,
    *,
    inputs: list[Path] | None = None,
    code_paths: list[Path] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    from scripts.artifact_state import resolve_artifact, _hash_target
    if not command:
        raise ValueError("a non-empty command is required")
    def hashes(paths):
        result = {}
        for value in paths or []:
            target = resolve_artifact(str(value), root)
            if not target.exists():
                raise FileNotFoundError(target)
            result[target.relative_to(root.resolve()).as_posix()] = _hash_target(target)
        return result
    input_hashes, code_hashes = hashes(inputs), hashes(code_paths)
    commit, dirty = _git_state()
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_dir = Path(runs_root) / run_id
    for sub in ("config", "figures", "tables", "artifacts"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": commit,
        "git_dirty": dirty,
        "input_hashes": input_hashes,
        "code_hashes": code_hashes,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False,
                                                   separators=(",", ":")).encode()).hexdigest(),
        "config": config,
        "random_seeds": {k: int(v) for k, v in seeds.items()},
        "dependency_versions": _dep_versions(),
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "hardware": {"cpu": platform.processor() or "unknown", "memory_gb": None},
        "command": [str(c) for c in command],
        "outputs": [],
        "metrics": {},
        "runtime_seconds": None,
        "parent_run": parent_run,
        "model_spec_version": _spec_version(),
        "notes": "",
    }
    (run_dir / "config" / "resolved.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "manifest.pending.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"record": record, "dir": run_dir}


def add_output(run: dict[str, Any], path: Path, kind: str) -> None:
    """Register an output file (copied under the run dir or already inside it)."""
    run_dir: Path = run["dir"]
    path = Path(path)
    if kind not in {"metrics", "figure", "table", "artifact", "stdout", "stderr"}:
        raise ValueError(f"unknown output kind: {kind}")
    if not path.is_file():
        raise FileNotFoundError(path)
    if run_dir.resolve() not in path.resolve().parents:
        target = run_dir / "artifacts" / path.name
        if target.exists() and sha256_file(target) != sha256_file(path):
            raise ValueError(f"output name collision: {path.name}")
        target.write_bytes(path.read_bytes())
        path = target
    run["record"]["outputs"].append(
        {"path": path.relative_to(run_dir).as_posix(), "sha256": sha256_file(path), "kind": kind}
    )


def finalize_run(
    run: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    runtime_seconds: float | None = None,
    notes: str = "",
) -> Path:
    record = run["record"]
    if (Path(run["dir"]) / "manifest.json").exists():
        raise ValueError("finalized run is immutable; create a new run")
    record["metrics"] = metrics or {}
    record["runtime_seconds"] = runtime_seconds
    record["notes"] = notes
    errors = validate_run_record(record, Path(run["dir"]), check_inputs=False)
    if errors:
        raise ValueError("; ".join(errors))
    final = run["dir"] / "manifest.json"
    final.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run["dir"] / "manifest.pending.json").unlink(missing_ok=True)
    index = Path(run["dir"]).parent / "registry.csv"
    is_new = not index.exists()
    with index.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(["run_id", "timestamp", "model_spec_version", "git_dirty", "primary_metric"])
        primary = next(iter((record["metrics"] or {}).values()), "")
        writer.writerow([record['run_id'], record['timestamp'], record['model_spec_version'], record['git_dirty'], primary])
    return final


def validate_run_record(record: dict[str, Any], run_dir: Path, *, root: Path = ROOT,
                        check_inputs: bool = True) -> list[str]:
    """Read-only provenance verification, suitable for validator and paper checks."""
    from scripts.artifact_state import resolve_artifact, _hash_target
    import jsonschema
    schema = json.loads((ROOT / "90_工具与配置/schemas/run-record.schema.json").read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(record)]
    if errors:
        return errors
    expected_config = hashlib.sha256(json.dumps(record["config"], sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")).encode()).hexdigest()
    if record.get("config_sha256") != expected_config:
        errors.append("config hash changed or absent")
    resolved = Path(run_dir) / "config/resolved.json"
    if not resolved.is_file() or json.loads(resolved.read_text(encoding="utf-8")) != record["config"]:
        errors.append("resolved config differs from manifest")
    if check_inputs:
        for category in ("input_hashes", "code_hashes"):
            for dep, expected in record.get(category, {}).items():
                try:
                    if _hash_target(resolve_artifact(dep, root)) != expected:
                        errors.append(f"{category}: {dep} changed")
                except ValueError as exc:
                    errors.append(str(exc))
    for output in record["outputs"]:
        try:
            target = resolve_artifact(output["path"], Path(run_dir))
            if not target.is_file() or sha256_file(target) != output["sha256"]:
                errors.append(f"output changed or missing: {output['path']}")
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def minimal_repro_command(record: dict[str, Any], run_dir: Path) -> str:
    """The single command that best reproduces this run from its manifest."""
    cmd = " ".join(record["command"])
    return f'(cd "{Path(__file__).resolve().parents[2]}" && {cmd})  # run dir: {run_dir.name}'


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Inspect run records.")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--show", metavar="RUN_ID")
    args = parser.parse_args()
    if args.show:
        manifest = Path(RUNS_ROOT) / args.show / "manifest.json"
        print(manifest.read_text(encoding="utf-8") if manifest.is_file() else f"missing: {manifest}")
        return 0
    for manifest in sorted(Path(RUNS_ROOT).glob("*/manifest.json")):
        record = json.loads(manifest.read_text(encoding="utf-8"))
        print(record["run_id"], record["model_spec_version"], json.dumps(record["metrics"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
