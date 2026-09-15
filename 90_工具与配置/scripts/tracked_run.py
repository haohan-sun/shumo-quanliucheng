"""Execute a command while producing an immutable reproducibility run record.

This is the supported execution wrapper for formal computations.  It creates the
record before starting the child, captures both streams, hashes declared inputs,
code, and outputs, and finalizes the record even when the child fails or times out.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, work_root
from scripts.artifact_state import resolve_artifact
from scripts.run_record import add_output, create_run, finalize_run

TIMEOUT_EXIT_CODE = 124
TRACKING_EXIT_CODE = 2
OUTPUT_KINDS = {"metrics", "figure", "table", "artifact"}


def _inside_existing_directory(value: str | Path, root: Path) -> Path:
    target = resolve_artifact(str(value), root)
    if not target.is_dir():
        raise ValueError(f"working directory is missing or not a directory: {value}")
    return target


def _declared_paths(values: Sequence[str | Path] | None, root: Path) -> list[Path]:
    return [resolve_artifact(str(value), root) for value in values or ()]


def _output_spec(value: str, root: Path) -> tuple[Path, str]:
    """Parse KIND=PATH, using artifact when no recognized kind is supplied."""
    prefix, separator, remainder = value.partition("=")
    if separator and prefix in OUTPUT_KINDS:
        if not remainder:
            raise ValueError("output path must not be empty")
        return resolve_artifact(remainder, root), prefix
    return resolve_artifact(value, root), "artifact"


def execute_tracked(
    command: Sequence[str],
    *,
    config: dict[str, Any] | None = None,
    seeds: dict[str, int] | None = None,
    inputs: Sequence[str | Path] | None = None,
    code_paths: Sequence[str | Path] | None = None,
    outputs: Sequence[tuple[str | Path, str] | str | Path] | None = None,
    timeout: float | None = None,
    cwd: str | Path = ".",
    root: Path = ROOT,
    runs_root: Path | None = None,
    parent_run: str | None = None,
) -> tuple[int, Path]:
    """Run ``command`` without a shell and return ``(exit_code, manifest_path)``."""
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("command must contain non-empty string arguments")
    if timeout is not None and timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    project_root = Path(root).resolve()
    run_cwd = _inside_existing_directory(cwd, project_root)
    input_paths = _declared_paths(inputs, project_root)
    source_paths = _declared_paths(code_paths, project_root)
    normalized_outputs: list[tuple[Path, str]] = []
    for output in outputs or ():
        if isinstance(output, tuple):
            path, kind = output
            if kind not in OUTPUT_KINDS:
                raise ValueError(f"unsupported declared output kind: {kind}")
            normalized_outputs.append((resolve_artifact(str(path), project_root), kind))
        else:
            normalized_outputs.append((resolve_artifact(str(output), project_root), "artifact"))

    target_runs = Path(runs_root) if runs_root is not None else work_root(project_root) / "runs"
    # A custom runs root is useful for tests, but may never point outside the workspace.
    target_runs = resolve_artifact(str(target_runs), project_root)
    run = create_run(
        config=config or {},
        seeds=seeds or {},
        command=list(command),
        parent_run=parent_run,
        runs_root=target_runs,
        inputs=input_paths,
        code_paths=source_paths,
        root=project_root,
    )
    stdout_path = Path(run["dir"]) / "stdout.log"
    stderr_path = Path(run["dir"]) / "stderr.log"
    started = time.monotonic()
    exit_code = TRACKING_EXIT_CODE
    timed_out = False
    execution_error: str | None = None

    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            try:
                completed = subprocess.run(
                    list(command),
                    cwd=run_cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    timeout=timeout,
                    check=False,
                    shell=False,
                )
                exit_code = int(completed.returncode)
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = TIMEOUT_EXIT_CODE
                stderr_handle.write(
                    f"\ntracked_run: command timed out after {timeout} seconds\n".encode()
                )
            except OSError as exc:
                execution_error = f"could not start command: {exc}"
                stderr_handle.write((f"\ntracked_run: {execution_error}\n").encode())

        add_output(run, stdout_path, "stdout")
        add_output(run, stderr_path, "stderr")
        missing: list[str] = []
        for output_path, kind in normalized_outputs:
            if output_path.is_file():
                add_output(run, output_path, kind)
            else:
                missing.append(output_path.relative_to(project_root).as_posix())
        if missing and exit_code == 0:
            exit_code = TRACKING_EXIT_CODE
        details = [f"status={'timeout' if timed_out else 'completed'}"]
        if execution_error:
            details.append(execution_error)
        if missing:
            details.append("missing declared outputs: " + ", ".join(missing))
        manifest = finalize_run(
            run,
            metrics={"exit_code": exit_code, "timed_out": timed_out},
            runtime_seconds=time.monotonic() - started,
            notes="; ".join(details),
        )
        return exit_code, manifest
    except Exception:
        # Finalization failures are exceptional: retain the pending record and logs
        # instead of fabricating a valid manifest.
        raise


def _load_config(value: str, root: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        path = resolve_artifact(value, root)
        if not path.is_file():
            raise ValueError(
                f"config is neither inline JSON nor a project file: {value}"
            ) from None
        parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("config JSON must be an object")
    return parsed


def _parse_seeds(values: Sequence[str]) -> dict[str, int]:
    seeds: dict[str, int] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key or key in seeds:
            raise ValueError(f"seed must be a unique NAME=INTEGER pair: {value}")
        seeds[key] = int(raw)
    return seeds


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if "--" not in raw_args:
        print("tracked_run: command must follow --", file=sys.stderr)
        return TRACKING_EXIT_CODE
    separator = raw_args.index("--")
    option_args, command = raw_args[:separator], raw_args[separator + 1 :]
    parser = argparse.ArgumentParser(description="Run a formal computation with provenance.")
    parser.add_argument("--config", default="{}", help="inline JSON object or project JSON path")
    parser.add_argument("--seed", action="append", default=[], metavar="NAME=INTEGER")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--code", action="append", default=[])
    parser.add_argument("--output", action="append", default=[], metavar="[KIND=]PATH")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--parent-run")
    try:
        args = parser.parse_args(option_args)
        if not command:
            raise ValueError("command after -- must not be empty")
        project_root = ROOT.resolve()
        output_specs = [_output_spec(value, project_root) for value in args.output]
        exit_code, manifest = execute_tracked(
            command,
            config=_load_config(args.config, project_root),
            seeds=_parse_seeds(args.seed),
            inputs=args.input,
            code_paths=args.code,
            outputs=output_specs,
            timeout=args.timeout,
            cwd=args.cwd,
            root=project_root,
            parent_run=args.parent_run,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"tracked_run: {exc}", file=sys.stderr)
        return TRACKING_EXIT_CODE
    print(manifest)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
