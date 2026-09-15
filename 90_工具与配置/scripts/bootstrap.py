#!/usr/bin/env python3
"""Idempotent project bootstrap: verify Python, create ``.venv``, install dependencies.

This script is the only place that provisions the environment.  It is invoked by
``setup.ps1`` / ``setup.sh`` (and by ``run.ps1 setup``), and is deliberately
runnable with *any* suitable system interpreter, because the project interpreter
does not exist yet on a fresh clone.

Design rules:

* no absolute paths, no assumptions about the author's machine;
* a broken or wrong-version ``.venv`` is reported with an actionable fix;
* installing the optional dependency groups is explicit, never implicit;
* the script never approves a Human Gate and never touches contest artifacts.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
TOOLS_ROOT = ROOT / "90_工具与配置"
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

OPTIONAL_GROUPS = ("optimization", "geospatial", "visualization", "document")
# Everything the deterministic CLI and the test suite import directly.  These are
# verified after install so a half-finished environment never looks "ready".
RUNTIME_MODULES = (
    "yaml",
    "jsonschema",
    "pytest",
    "numpy",
    "pandas",
    "matplotlib",
)
CI_MODULES = RUNTIME_MODULES

SETUP_HELP = """\
next steps
  Windows (PowerShell) :  .\\run.ps1 doctor
  Windows (cmd.exe)    :  run.ps1 doctor
  POSIX                :  ./run.sh doctor
"""


class BootstrapError(RuntimeError):
    """A condition the user must fix; always printed without a traceback."""


def read_pyproject() -> dict:
    if not PYPROJECT.is_file():
        raise BootstrapError(f"pyproject.toml not found at {PYPROJECT}")
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def requires_python_spec() -> str:
    spec = read_pyproject().get("project", {}).get("requires-python")
    if not spec:
        raise BootstrapError("pyproject.toml does not declare project.requires-python")
    return str(spec)


def parse_spec(spec: str) -> list[tuple[str, tuple[int, ...]]]:
    """Parse a PEP 440 version specifier set into (operator, version) pairs."""
    clauses: list[tuple[str, tuple[int, ...]]] = []
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        match = re.fullmatch(r"(==|!=|>=|<=|>|<|~=)\s*(\d+(?:\.\d+)*)", raw)
        if not match:
            raise BootstrapError(f"unsupported requires-python clause: {raw!r}")
        operator, version = match.group(1), match.group(2)
        clauses.append((operator, tuple(int(part) for part in version.split("."))))
    if not clauses:
        raise BootstrapError(f"could not parse requires-python: {spec!r}")
    return clauses


def _pad(version: tuple[int, ...], width: int) -> tuple[int, ...]:
    return version + (0,) * max(0, width - len(version))


def satisfies(version: tuple[int, ...], spec: str) -> bool:
    for operator, bound in parse_spec(spec):
        width = max(len(version), len(bound))
        left, right = _pad(version, width), _pad(bound, width)
        if operator == ">=" and not left >= right:
            return False
        if operator == "<=" and not left <= right:
            return False
        if operator == ">" and not left > right:
            return False
        if operator == "<" and not left < right:
            return False
        if operator == "==" and left != right:
            return False
        if operator == "!=" and left == right:
            return False
        if operator == "~=":
            # Compatible release: >= bound and same major (for >=X.Y, also same minor).
            if left < right or left[0] != right[0]:
                return False
            if len(bound) >= 2 and left[1] != right[1]:
                return False
    return True


def interpreter_version(python: Path) -> tuple[int, ...] | None:
    try:
        result = subprocess.run(
            [str(python), "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def find_system_python(spec: str) -> tuple[Path, tuple[int, ...]]:
    """Find an interpreter that satisfies ``spec`` without assuming a machine layout."""
    candidates: list[list[str]] = []
    if os.name == "nt":
        candidates.extend([["py", "-3"], ["py"], ["python3"], ["python"]])
    else:
        candidates.extend([["python3"], ["python"]])
    seen: set[str] = set()
    rejected: list[str] = []
    for command in candidates:
        executable = shutil.which(command[0])
        if executable is None:
            continue
        key = " ".join([executable, *command[1:]])
        if key in seen:
            continue
        seen.add(key)
        probe = _probe_command(command)
        if probe is None:
            continue
        version = interpreter_version(probe)
        if version is None:
            continue
        if satisfies(version, spec):
            return probe, version
        rejected.append(f"{' '.join(command)} -> {'.'.join(map(str, version))}")
    detail = f" Rejected interpreters: {', '.join(rejected)}." if rejected else ""
    raise BootstrapError(
        f"no Python interpreter on PATH satisfies requires-python {spec}.{detail}\n"
        f"Install a supported Python (see {PYPROJECT.name}) and re-run setup."
    )


def _probe_command(command: list[str]) -> Path | None:
    """Return a directly executable interpreter path for ``command``."""
    if len(command) == 1:
        return Path(command[0])
    # 'py -3' style launchers: ask the launcher for the concrete executable.
    try:
        result = subprocess.run(
            [*command, "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    candidate = Path(result.stdout.strip())
    return candidate if candidate.is_file() else None


def venv_state(spec: str) -> tuple[str, tuple[int, ...] | None]:
    """Return ('ok'|'missing'|'wrong-version'|'broken', version)."""
    if not VENV_PYTHON.is_file():
        return ("missing", None)
    version = interpreter_version(VENV_PYTHON)
    if version is None:
        return ("broken", None)
    if not satisfies(version, spec):
        return ("wrong-version", version)
    return ("ok", version)


def missing_modules(python: Path, modules: tuple[str, ...]) -> list[str]:
    code = (
        "import importlib.util, sys\n"
        f"names = {list(modules)!r}\n"
        "print(' '.join(n for n in names if importlib.util.find_spec(n) is None))\n"
    )
    try:
        result = subprocess.run(
            [str(python), "-c", code], capture_output=True, text=True, check=True, timeout=120
        )
    except (OSError, subprocess.SubprocessError):
        return list(modules)
    return result.stdout.split()


def normalized_groups(raw: list[str]) -> list[str]:
    groups: list[str] = []
    for item in raw:
        for part in item.split(","):
            part = part.strip()
            if not part:
                continue
            if part not in OPTIONAL_GROUPS:
                raise BootstrapError(
                    f"unknown optional dependency group {part!r}; "
                    f"available: {', '.join(OPTIONAL_GROUPS)}"
                )
            if part not in groups:
                groups.append(part)
    return groups


def requirements_file(groups: list[str]) -> tuple[Path, list[str]]:
    """Write a plain requirements file from pyproject.toml.

    Installing from a requirements list instead of ``-e .`` keeps the step
    independent of the wheel build target: this project is a workspace, not a
    distributable library, and its tooling resolves imports via ``pythonpath``
    plus explicit ``sys.path`` insertion.
    """
    project = read_pyproject().get("project", {})
    required = list(project.get("dependencies", []))
    if not required:
        raise BootstrapError("pyproject.toml declares no [project].dependencies")
    optional = project.get("optional-dependencies", {})
    lines = [
        "# Generated by 90_工具与配置/scripts/bootstrap.py -- do not edit.",
        "# Source of truth: pyproject.toml [project].dependencies",
        *required,
    ]
    for group in groups:
        entries = optional.get(group)
        if not entries:
            raise BootstrapError(
                f"optional dependency group {group!r} is not declared in pyproject.toml"
            )
        lines.append(f"# --- optional group: {group} ---")
        lines.extend(entries)
    path = VENV / "requirements-setup.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, required


def run(command: list[str], *, label: str) -> None:
    print(f"$ {label}")
    env = dict(os.environ)
    env.setdefault("UV_CACHE_DIR", str(TOOLS_ROOT / ".cache" / "uv"))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if result.returncode:
        raise BootstrapError(f"command failed with exit code {result.returncode}: {label}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Provision the project virtual environment (idempotent).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=SETUP_HELP,
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and exit.")
    parser.add_argument("--ci", action="store_true", help="Required dependencies only; no doctor gate.")
    parser.add_argument(
        "--with-extras",
        action="append",
        default=[],
        metavar="GROUP",
        help=f"Optional dependency group(s): {', '.join(OPTIONAL_GROUPS)}.",
    )
    parser.add_argument("--force-recreate", action="store_true", help="Delete and recreate .venv.")
    parser.add_argument("--no-doctor", action="store_true", help="Skip the post-install doctor check.")
    parser.add_argument(
        "--installer", choices=["auto", "uv", "pip"], default="auto", help="uv when available, else pip."
    )
    args = parser.parse_args(argv)

    try:
        spec = requires_python_spec()
    except BootstrapError as error:
        print(f"setup: FAIL\n  {error}", file=sys.stderr)
        return 2

    print(f"project root        : {ROOT}")
    print(f"requires-python     : {spec}")

    try:
        groups = normalized_groups(args.with_extras)
    except BootstrapError as error:
        print(f"setup: FAIL\n  {error}", file=sys.stderr)
        return 2

    if args.force_recreate and VENV.exists():
        print(f"removing existing environment: {VENV}")
        if not args.dry_run:
            shutil.rmtree(VENV, ignore_errors=True)

    state, version = venv_state(spec)
    print(f"virtual environment : {VENV} ({state}{'' if version is None else ' ' + '.'.join(map(str, version))})")

    target_python: Path | None = VENV_PYTHON if state == "ok" else None
    if state == "wrong-version":
        print(
            f"setup: FAIL\n  the existing environment uses Python {'.'.join(map(str, version or ()))}, "
            f"which does not satisfy {spec}.\n  Fix: re-run setup with --force-recreate.",
            file=sys.stderr,
        )
        return 2
    if state == "broken":
        print(
            "setup: FAIL\n  the existing environment cannot report its version.\n"
            "  Fix: re-run setup with --force-recreate.",
            file=sys.stderr,
        )
        return 2

    if target_python is None:
        try:
            system_python, system_version = find_system_python(spec)
        except BootstrapError as error:
            print(f"setup: FAIL\n  {error}", file=sys.stderr)
            return 2
        print(f"base interpreter    : {system_python} ({'.'.join(map(str, system_version))})")

    installer = args.installer
    if installer == "auto":
        installer = "uv" if shutil.which("uv") else "pip"
    if installer == "uv" and not shutil.which("uv"):
        raise SystemExit(print("setup: FAIL\n  --installer uv requested but uv is not on PATH", file=sys.stderr) or 2)
    print(f"installer           : {installer}")
    print(f"optional groups     : {', '.join(groups) if groups else 'none'}")

    try:
        requirements, required_specs = requirements_file(groups)
    except BootstrapError as error:
        print(f"setup: FAIL\n  {error}", file=sys.stderr)
        return 2
    print(f"requirements        : {requirements} ({len(required_specs)} required entries)")

    plan: list[tuple[list[str], str]] = []
    if target_python is None:
        plan.append(([str(system_python), "-m", "venv", str(VENV)], f"create {VENV.name}"))
        target_python = VENV_PYTHON

    if installer == "uv":
        plan.append(
            (
                ["uv", "pip", "install", "--python", str(VENV_PYTHON), "-r", str(requirements)],
                "install dependencies (uv pip)",
            )
        )
    else:
        plan.append(
            (
                [
                    str(VENV_PYTHON),
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--disable-pip-version-check",
                    "pip",
                ],
                "upgrade pip",
            )
        )
        plan.append(
            (
                [
                    str(VENV_PYTHON),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(requirements),
                ],
                "install dependencies (pip)",
            )
        )

    if args.dry_run:
        print("\nplan (dry run; nothing was executed):")
        for command, label in plan:
            print(f"  {label}: {' '.join(command)}")
        return 0

    for command, label in plan:
        try:
            run(command, label=label)
        except BootstrapError as error:
            print(f"setup: FAIL\n  {error}", file=sys.stderr)
            return 1

    if not VENV_PYTHON.is_file():
        print(
            f"setup: FAIL\n  expected interpreter was not created: {VENV_PYTHON}", file=sys.stderr
        )
        return 1

    required = CI_MODULES if args.ci else RUNTIME_MODULES
    absent = missing_modules(VENV_PYTHON, required)
    if absent:
        print(
            "setup: FAIL\n  dependencies are still missing after install: "
            + ", ".join(absent)
            + "\n  Re-run setup and read the installer output above.",
            file=sys.stderr,
        )
        return 1

    print(f"environment ready   : {VENV_PYTHON}")

    if not args.no_doctor and not args.ci:
        code = subprocess.run(
            [str(VENV_PYTHON), str(TOOLS_ROOT / "scripts" / "doctor.py")],
            cwd=ROOT,
            check=False,
        ).returncode
        if code:
            print(
                "setup: WARNING\n  the environment is installed but 'doctor' reported problems.\n"
                "  Review the report above; missing optional tools (pandoc/LaTeX) only affect "
                "paper rendering.",
                file=sys.stderr,
            )

    print("setup: OK")
    print(SETUP_HELP)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as error:
        print(f"setup: FAIL\n  {error}", file=sys.stderr)
        raise SystemExit(1) from None
