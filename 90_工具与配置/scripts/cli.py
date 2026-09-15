#!/usr/bin/env python3
"""Cross-platform command runner for the mathematical-modeling workspace.

This is the single source of truth for the project CLI.  ``run.ps1`` and
``run.sh`` are thin wrappers that only locate the project interpreter and call
this module, so Windows and POSIX behaviour cannot drift apart.

Every command delegates to an existing project script; no behaviour is
reimplemented here.  Commands that must never be automated (Human Gate
approval) are deliberately absent from this dispatcher and remain in
``scripts/gate_control.py``, where they require an explicit human decision.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, TOOLS_ROOT, load_layout, tools_root, work_root

SCRIPTS = TOOLS_ROOT / "scripts"

VENV_PYTHON_CANDIDATES = (
    Path(".venv") / "Scripts" / "python.exe",
    Path(".venv") / "bin" / "python",
)
SETUP_HINT = (
    "Run the setup step first:\n"
    "  Windows :  .\\setup.ps1\n"
    "  POSIX   :  ./setup.sh"
)

if os.name == "nt":
    SETUP_HINT = (
        "Run the setup step first:\n"
        "  PowerShell :  .\\setup.ps1\n"
        "  cmd.exe    :  setup.ps1\n"
        "  Git Bash   :  ./setup.sh"
    )

# Commands the documentation promises.  ``test_cli_commands.py`` asserts both
# directions: every name here is reachable, and the set matches the README.
DOCUMENTED_COMMANDS = (
    "setup",
    "doctor",
    "status",
    "validate",
    "test",
    "verify",
    "package",
    "clean",
    "skills",
    "agents",
    "gates",
    "modes",
    "demo",
    "info",
    "route",
    "plan",
    "hash",
    "compliance",
    "git-status",
)


def project_python(root: Path = ROOT) -> Path | None:
    """Return the project interpreter, or ``None`` when setup has not run."""
    for relative in VENV_PYTHON_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def _require_python() -> Path:
    python = project_python()
    if python is not None:
        return python
    expected = " or ".join((ROOT / relative).as_posix() for relative in VENV_PYTHON_CANDIDATES)
    print("project virtual environment: MISSING", file=sys.stderr)
    print(f"  expected interpreter: {expected}", file=sys.stderr)
    print(SETUP_HINT, file=sys.stderr)
    raise SystemExit(2)


def _run_module(module: str, argv: list[str], *, label: str | None = None) -> int:
    """Run a project script with the project interpreter from the repo root."""
    python = _require_python()
    command = [str(python), str(SCRIPTS / module), *argv]
    if label:
        print(f"$ {label}")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def cmd_setup(args: argparse.Namespace) -> int:
    return _run_module("bootstrap.py", list(args.setup_args))


def cmd_doctor(args: argparse.Namespace) -> int:
    return _run_module("doctor.py", ["--json"] if args.json else [])


def cmd_status(args: argparse.Namespace) -> int:
    return _run_module("status.py", ["--json"] if args.json else [])


def cmd_validate(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.with_tests:
        argv.append("--with-tests")
    if args.submission:
        argv.append("--submission")
    return _run_module("validate.py", argv)


def cmd_test(args: argparse.Namespace) -> int:
    python = _require_python()
    return subprocess.run(
        [str(python), "-m", "pytest", *args.pytest_args], cwd=ROOT, check=False
    ).returncode


def cmd_verify(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.json:
        argv.append("--json")
    if args.with_tests:
        argv.append("--with-tests")
    if args.write_report:
        argv.append("--write-report")
    return _run_module("verify.py", argv)


def cmd_package(args: argparse.Namespace) -> int:
    """Check or build the submission archive through the existing guard chain.

    ``package`` never approves G7 and never bypasses compliance, the independent
    verification record, or the package boundary rules.  When G7 is absent it
    reports ``submission readiness: BLOCKED`` and exits non-zero -- that is the
    correct behaviour, not a failure to fix.
    """
    argv = ["--build"] if args.build else ["--check"]
    if args.output:
        argv.extend(["--output", args.output])
    return _run_module("build_submission.py", argv)


def _git_tracked(root: Path) -> set[str] | None:
    """Tracked paths, or ``None`` when git metadata is unavailable.

    ``-z`` output is decoded explicitly as UTF-8: git writes raw bytes, and the
    default locale codec on a Chinese Windows install is GBK, so a repository with
    non-ASCII filenames would otherwise raise UnicodeDecodeError.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    text = result.stdout.decode("utf-8", errors="surrogateescape")
    return {item for item in text.split("\0") if item}


def cmd_clean(args: argparse.Namespace) -> int:
    """Remove regenerable caches.  Never touches a git-tracked file."""
    tools = tools_root(ROOT) if ROOT != tools_root(ROOT) else TOOLS_ROOT
    work = work_root(ROOT)
    targets = [
        tools / ".cache",
        tools / "reports" / "ENVIRONMENT_REPORT.md",
        work / "src" / "viz" / "__pycache__",
    ]
    targets.extend(path for path in work.rglob("__pycache__") if path.is_dir())
    targets = sorted({path for path in targets if path.exists()})

    tracked = _git_tracked(ROOT)
    removed: list[str] = []
    for target in targets:
        relative = target.relative_to(ROOT).as_posix()
        if tracked is None:
            print(f"skip (no git metadata, refusing to guess): {relative}")
            continue
        if any(entry == relative or entry.startswith(relative + "/") for entry in tracked):
            print(f"skip (tracked by git): {relative}")
            continue
        removed.append(relative)
        if args.dry_run:
            continue
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            target.unlink(missing_ok=True)

    verb = "would remove" if args.dry_run else "removed"
    if not removed:
        print("clean: nothing to remove")
        return 0
    for relative in removed:
        print(f"{verb}: {relative}")
    print(f"clean: {verb} {len(removed)} path(s)")
    return 0


def _list_names(directory: Path, suffix: str | None = None) -> int:
    if not directory.is_dir():
        print(f"missing directory: {directory.relative_to(ROOT).as_posix()}", file=sys.stderr)
        return 1
    names: list[str] = []
    for entry in directory.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            names.append(entry.name)
            continue
        if suffix and not entry.name.endswith(suffix):
            continue
        names.append(entry.name[: -len(suffix)] if suffix else entry.name)
    for name in sorted(names):
        print(name)
    return 0


def cmd_skills(_: argparse.Namespace) -> int:
    layout = load_layout(ROOT)
    skills_root = ROOT / str(layout.get("tool_root", ".")) / ".agents" / "skills"
    return _list_names(skills_root)


def cmd_agents(_: argparse.Namespace) -> int:
    layout = load_layout(ROOT)
    agents_root = ROOT / str(layout.get("tool_root", ".")) / ".codex" / "agents"
    return _list_names(agents_root, suffix=".toml")


def cmd_gates(args: argparse.Namespace) -> int:
    return _run_module("gate_control.py", ["status"])


def cmd_modes(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.mode:
        argv.extend(["--mode", args.mode])
    if args.validate:
        argv.append("--validate")
    if args.json:
        argv.append("--json")
    return _run_module("workflow_mode.py", argv)


def cmd_demo(args: argparse.Namespace) -> int:
    argv = list(args.demo_args)
    if argv and argv[0] == "--":
        argv = argv[1:]
    return _run_module("run_demo.py", argv)


def cmd_route(args: argparse.Namespace) -> int:
    argv = [args.request]
    if args.not_project:
        argv.append("--not-project")
    return _run_module("auto_route.py", argv)


def cmd_plan(args: argparse.Namespace) -> int:
    argv = [args.request]
    if args.json:
        argv.append("--json")
    return _run_module("decompose.py", argv)


def cmd_hash(args: argparse.Namespace) -> int:
    argv = ["--update"] if args.update else []
    return _run_module("hash_inputs.py", argv)


def cmd_compliance(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.submission:
        argv.append("--submission")
    if args.json:
        argv.append("--json")
    if args.write:
        argv.append("--write")
    return _run_module("compliance.py", argv)


def cmd_git_status(_: argparse.Namespace) -> int:
    safe_path = ROOT.as_posix()
    return subprocess.run(
        ["git", "-c", f"safe.directory={safe_path}", "-C", str(ROOT), "status", "--short"],
        check=False,
    ).returncode


def cmd_info(_: argparse.Namespace) -> int:
    python = project_python()
    print(f"repository root : {ROOT}")
    print(f"platform        : {sys.platform}")
    print(f"system python   : {sys.version.split()[0]} ({sys.executable})")
    if python is None:
        print("project python  : MISSING")
        print(SETUP_HINT)
    else:
        print(f"project python  : {python}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run",
        description=(
            "Mathematical-modeling workspace CLI. Human Gate approval is intentionally "
            "not available here: record it with scripts/gate_control.py after an explicit "
            "human decision."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  ./setup.ps1            create .venv and install dependencies\n"
            "  ./run.ps1 doctor       check interpreter, dependencies and tools\n"
            "  ./run.ps1 validate     structure + contract checks\n"
            "  ./run.ps1 test         run the pytest suite\n"
            "  ./run.ps1 verify       full deterministic verification (no Gate approval)\n"
            "  ./run.ps1 package      check submission readiness (BLOCKED until G7)\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def add(name: str, func, help_text: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name, help=help_text, description=help_text)
        child.set_defaults(func=func)
        return child

    setup = add("setup", cmd_setup, "Create/refresh .venv and install dependencies (idempotent).")
    setup.add_argument("--dry-run", action="store_true", help="Print the plan without executing.")
    setup.add_argument("--ci", action="store_true", help="CI profile: required dependencies only.")
    setup.add_argument(
        "--with-extras",
        action="append",
        default=[],
        metavar="GROUP",
        help="Install an optional dependency group (optimization, geospatial, "
        "visualization, document). Repeatable or comma-separated.",
    )
    setup.add_argument(
        "--force-recreate",
        action="store_true",
        help="Delete and recreate .venv (use when the interpreter is wrong or broken).",
    )
    setup.add_argument(
        "--no-doctor",
        action="store_true",
        help="Skip the post-install doctor check.",
    )
    setup.add_argument(
        "--installer",
        choices=["auto", "uv", "pip"],
        default="auto",
        help="Dependency installer to use (default: uv when available, else pip).",
    )
    setup.add_argument(
        "setup_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded verbatim to scripts/bootstrap.py (use '--' before them).",
    )

    doctor = add("doctor", cmd_doctor, "Inspect interpreter, dependencies and external tools.")
    doctor.add_argument("--json", action="store_true")

    status = add("status", cmd_status, "Show canonical workflow state.")
    status.add_argument("--json", action="store_true")

    validate = add("validate", cmd_validate, "Run structure and contract validation.")
    validate.add_argument("--with-tests", action="store_true", help="Append the pytest suite.")
    validate.add_argument("--submission", action="store_true", help="Append compliance checks.")

    test = add("test", cmd_test, "Run the pytest suite.")
    test.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Extra arguments for pytest.")

    verify = add(
        "verify",
        cmd_verify,
        "Run deterministic verification (structure, contracts, provenance, compliance, "
        "claims, gates, package boundary). Never records an independent verification.",
    )
    verify.add_argument("--json", action="store_true")
    verify.add_argument("--with-tests", action="store_true", help="Include the pytest suite.")
    verify.add_argument(
        "--write-report",
        action="store_true",
        help="Write reports/verify-run.json (never overwrites reports/verify.json).",
    )

    package = add(
        "package",
        cmd_package,
        "Check or build the submission package through the full guard chain.",
    )
    package.add_argument("--build", action="store_true", help="Build the archive after all guards pass.")
    package.add_argument("--output", metavar="PATH", help="Archive path (default: 04_论文与提交/submission/…).")

    clean = add("clean", cmd_clean, "Remove regenerable caches (never removes tracked files).")
    clean.add_argument("--dry-run", action="store_true")

    add("skills", cmd_skills, "List project Skills.")
    add("agents", cmd_agents, "List project Agents.")
    add("gates", cmd_gates, "Read-only G1-G7 Human Gate status.")
    add("info", cmd_info, "Show resolved paths and interpreter.")

    modes = add(
        "modes",
        cmd_modes,
        "Inspect research/competition workflow modes (never weakens a Gate decision).",
    )
    modes.add_argument("--mode", choices=["research", "competition"], help="Inspect one mode.")
    modes.add_argument("--validate", action="store_true", help="Validate the mode configuration.")
    modes.add_argument("--json", action="store_true")

    demo = add("demo", cmd_demo, "Run or re-check the toy end-to-end demo.")
    demo.add_argument(
        "demo_args",
        nargs=argparse.REMAINDER,
        help="Arguments for scripts/run_demo.py, e.g. --check-only (use '--' before them).",
    )

    route = add("route", cmd_route, "Preview deterministic routing for one request.")
    route.add_argument("request")
    route.add_argument("--not-project", action="store_true")

    plan = add("plan", cmd_plan, "Decompose a complex request into a routed task DAG.")
    plan.add_argument("request")
    plan.add_argument("--json", action="store_true")

    hash_cmd = add("hash", cmd_hash, "Hash official inputs, optionally updating the manifest.")
    hash_cmd.add_argument("--update", action="store_true")

    compliance = add("compliance", cmd_compliance, "Run rule-backed compliance checks.")
    compliance.add_argument("--submission", action="store_true")
    compliance.add_argument("--json", action="store_true")
    compliance.add_argument("--write", action="store_true")

    add("git-status", cmd_git_status, "Short git status of this repository.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    # Bare invocation and an explicit `help` both print the command list on
    # stdout and succeed: a stranger running `run.ps1` with no argument should
    # see what is available, not an argparse error.
    if not argv or argv[0] in {"help", "--help", "-h"}:
        parser.print_help(file=sys.stdout)
        return 0
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        parser.print_help(file=sys.stdout)
        return 0
    if args.command == "setup" and args.setup_args and args.setup_args[0] == "--":
        args.setup_args = args.setup_args[1:]
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
