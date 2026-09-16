"""Tests for the stranger-facing surface: CLI, verify, package, bootstrap, demo.

These guard what a new user hits first.  They deliberately avoid mocking the core
behaviour: `verify` and `package` run through their real entry points, and the
demo smoke test runs the real demo.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "90_工具与配置"
SCRIPTS = TOOLS / "scripts"
sys.path.insert(0, str(TOOLS))

README = ROOT / "README.md"

# Commands the README promises.  Kept here as data so the README cannot drift
# away from the implementation without failing a test.
DOCUMENTED_COMMANDS = (
    "setup",
    "doctor",
    "status",
    "validate",
    "test",
    "lint",
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


def _subcommand_names() -> set[str]:
    from scripts.cli import build_parser

    parser = build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and "validate" in choices and "doctor" in choices:
            return {name for name in choices if name != "help"}
    raise AssertionError("could not locate the subcommand table")


def test_documented_commands_are_registered():
    names = _subcommand_names()
    missing = [name for name in DOCUMENTED_COMMANDS if name not in names]
    assert missing == [], f"documented but not implemented: {missing}"


def test_command_table_and_declaration_agree():
    from scripts.cli import DOCUMENTED_COMMANDS as declared

    assert set(declared) == _subcommand_names()


def test_readme_documents_every_command():
    text = README.read_text(encoding="utf-8")
    missing = [
        name
        for name in DOCUMENTED_COMMANDS
        if f"run.ps1 {name}" not in text and f"`run.ps1 {name}`" not in text
    ]
    assert missing == [], f"README does not document: {missing}"


def test_readme_never_promises_a_missing_command():
    text = README.read_text(encoding="utf-8")
    names = _subcommand_names()
    invoked = set(re.findall(r"run\.(?:ps1|sh)\s+([a-z][a-z-]*)", text))
    invoked.discard("help")
    unknown = sorted(
        name for name in invoked if name not in names and not any(n.startswith(name) for n in names)
    )
    assert unknown == [], f"README invokes non-existent commands: {unknown}"


def test_bare_invocation_prints_help_and_succeeds():
    from scripts.cli import main

    assert main([]) == 0
    assert main(["help"]) == 0


def test_missing_venv_exits_with_actionable_message(capsys):
    from scripts import cli

    original = cli.project_python
    cli.project_python = lambda root=None: None  # type: ignore[assignment]
    try:
        with pytest.raises(SystemExit) as excinfo:
            cli._require_python()
    finally:
        cli.project_python = original  # type: ignore[assignment]
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "setup.ps1" in captured.err
    assert "setup.sh" in captured.err


def test_agent_listing_strips_the_toml_suffix():
    names = sorted(
        entry.name[: -len(".toml")]
        for entry in (TOOLS / ".codex" / "agents").iterdir()
        if entry.name.endswith(".toml")
    )
    assert "critic" in names
    assert all(not name.endswith(".t") for name in names)


def test_clean_never_targets_a_tracked_file():
    from scripts.cli import _git_tracked

    tracked = _git_tracked(ROOT)
    if tracked is None:
        pytest.skip("git metadata unavailable")
    assert "run.ps1" in tracked
    assert not any(entry.endswith("__pycache__") for entry in tracked)


# --------------------------------------------------------------------------
# verify / package entry points
# --------------------------------------------------------------------------
def test_verify_report_is_never_marked_verified():
    from scripts.verify import run_checks

    report = run_checks(with_tests=False)
    assert report["root"] == ROOT.as_posix()
    ids = {item["check_id"] for item in report["checks"]}
    assert {"structure", "contracts", "human_gates", "package_boundary"} <= ids
    record = json.loads((TOOLS / "reports" / "verify.json").read_text(encoding="utf-8"))
    assert record["status"] == "pending"
    assert record["verified_at"] is None


def test_verify_cli_passes_and_leaves_the_human_record_alone():
    before = (TOOLS / "reports" / "verify.json").read_bytes()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verification run: PASS" in result.stdout
    assert (TOOLS / "reports" / "verify.json").read_bytes() == before


def test_verify_write_report_uses_a_separate_path():
    from scripts.verify import REPORT_PATH

    assert REPORT_PATH.name == "verify-run.json"
    assert REPORT_PATH != TOOLS / "reports" / "verify.json"


def test_verify_does_not_approve_or_touch_a_gate():
    from scripts._project import load_json
    from scripts.auto_route import valid_human_gate
    from scripts.verify import run_checks

    manifest_path = ROOT / "run-manifest.json"
    before = manifest_path.read_bytes()
    run_checks(with_tests=False)
    assert manifest_path.read_bytes() == before
    manifest = load_json(manifest_path)
    assert not any(valid_human_gate(manifest, f"G{n}") for n in range(1, 8))


def test_package_is_blocked_without_g7_and_creates_nothing(tmp_path):
    output = tmp_path / "should-not-exist.zip"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_submission.py"), "--build", "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "submission readiness: BLOCKED" in result.stdout
    assert "G7" in result.stdout
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_readiness_blockers_survive_a_missing_workspace(tmp_path):
    """A clean checkout must report blockers, not raise."""
    from scripts.build_submission import readiness_blockers

    blockers = readiness_blockers(tmp_path)
    assert blockers
    assert all(isinstance(item, str) and item for item in blockers)
    assert any("verify.json" in item for item in blockers)


def test_package_files_skips_interpreter_caches():
    from scripts.build_submission import PRUNED_CACHE_DIRS

    assert "__pycache__" in PRUNED_CACHE_DIRS


def test_junction_detection_works_without_python312(monkeypatch):
    """`os.path.isjunction` is 3.12+; the project supports 3.11.

    CI caught this as `AttributeError: module 'posixpath' has no attribute
    'isjunction'`, which made the whole package-boundary check fail on 3.11.
    """
    import os

    from scripts import package_guard

    monkeypatch.setattr(package_guard, "_HAS_ISJUNCTION", False)
    assert package_guard.is_link_like(ROOT / "run.ps1") is False
    assert package_guard.is_link_like(ROOT / "90_工具与配置") is False
    assert package_guard.is_link_like(ROOT / "definitely-missing") is False
    assert package_guard.check_target(ROOT / "90_工具与配置" / "scripts") == []
    assert os.path.__name__ in {"ntpath", "posixpath"}


def test_junction_detection_still_reports_a_symlink(tmp_path):
    from scripts import package_guard

    (tmp_path / "real.txt").write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(tmp_path / "real.txt")
    except (OSError, NotImplementedError):
        pytest.skip("creating symlinks is not permitted in this environment")
    assert package_guard.is_link_like(link) is True


def test_dependency_guard_accepts_a_relative_directory():
    """A relative target used to raise ValueError from pathlib.relative_to."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "package_guard.py"),
            "90_工具与配置/scripts",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "package boundary: PASS" in result.stdout


def test_resolve_python_returns_a_real_path():
    """A tracked run must record an interpreter path that exists.

    On POSIX ``sys.executable`` is ``<venv>/bin/python`` — a symlink into the base
    interpreter outside the project — and a tracked run rejected it as an artifact
    escaping the workspace, which broke the demo on Linux CI.
    """
    from pathlib import Path as _Path

    from scripts._project import resolve_python

    resolved = resolve_python()
    assert _Path(resolved).is_file()
    assert "python" in _Path(resolved).name.lower()


def test_demo_records_the_resolved_interpreter():
    """The demo must not hand a venv symlink to the tracked-run machinery."""
    import scripts.run_demo as demo

    source = demo.__file__
    assert source is not None
    text = Path(source).read_text(encoding="utf-8")
    assert "sys.executable" not in text, (
        "run_demo must use resolve_python() so POSIX venv symlinks stay inside the project"
    )
    assert "resolve_python()" in text


def test_doctor_recognises_the_active_project_environment():
    """`doctor` must not report the project environment as inactive.

    `validate` starts child processes, and a child that was launched through a
    resolved interpreter path reports the *base* ``sys.prefix``. A false negative
    here made the validation step fail on Linux CI.
    """
    from scripts.doctor import project_venv_active

    assert project_venv_active() is True


def test_subprocess_scripts_keep_the_virtual_environment(monkeypatch):
    """Spawned helpers must use sys.executable, not a resolved path.

    Resolving the interpreter drops the venv from sys.prefix inside the child,
    which is what made `doctor` fail when `validate` was changed to resolve it.
    """
    for name in ("validate.py", "verify.py", "lifecycle_hooks.py"):
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "sys.executable" in text, f"{name} should start children with sys.executable"
        assert "resolve_python()" not in text, (
            f"{name} must not resolve the interpreter for subprocesses"
        )


def test_a_working_directory_is_not_scanned_for_links(tmp_path):
    """A tracked run must accept a cwd that merely *contains* an external link.

    On POSIX ``<venv>/bin/python`` is a symlink to the base interpreter, so
    scanning every child of the repository root rejected the whole run with
    "artifact link outside project". A working directory is a location, not
    content, so only the directory itself is validated.
    """
    from scripts.artifact_state import resolve_artifact

    root = tmp_path
    (root / "work").mkdir()
    outside = tmp_path.parent / "outside-target.txt"
    outside.write_text("x", encoding="utf-8")
    link = root / "work" / "python"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("creating symlinks is not permitted in this environment")

    # As a location: accepted.
    assert resolve_artifact("work", root, scan_children=False) == (root / "work").resolve()
    # As content: still rejected, because a Gate dependency must not escape.
    with pytest.raises(ValueError, match="artifact link outside project"):
        resolve_artifact("work", root)


# --------------------------------------------------------------------------
# bootstrap
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ((3, 10, 0), False),
        ((3, 11, 0), True),
        ((3, 12, 7), True),
        ((3, 13, 1), True),
        ((3, 14, 0), False),
    ],
)
def test_version_gate_matches_pyproject(version, expected):
    from scripts.bootstrap import requires_python_spec, satisfies

    assert satisfies(version, requires_python_spec()) is expected


def test_bootstrap_dry_run_reports_a_plan():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "bootstrap.py"), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "requires-python" in result.stdout
    assert "plan (dry run" in result.stdout


def test_bootstrap_rejects_an_unknown_dependency_group():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "bootstrap.py"), "--dry-run", "--with-extras", "nope"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unknown optional dependency group" in result.stderr


def test_shell_entries_exist_and_ps1_stays_ascii():
    """Windows PowerShell 5.1 decodes a BOM-less script as ANSI."""
    for name in ("setup.ps1", "run.ps1"):
        path = ROOT / name
        assert path.is_file(), f"{name} is missing"
        non_ascii = [byte for byte in path.read_bytes() if byte > 0x7F]
        assert non_ascii == [], (
            f"{name} contains non-ASCII bytes; PowerShell 5.1 would fail to parse it"
        )
    for name in ("setup.sh", "run.sh"):
        assert (ROOT / name).is_file(), f"{name} is missing"


def test_run_ps1_prints_the_actionable_next_step():
    text = (ROOT / "run.ps1").read_text(encoding="utf-8")
    assert "Project Python is missing" in text
    assert "setup.ps1" in text


# --------------------------------------------------------------------------
# demo
# --------------------------------------------------------------------------
def test_demo_runs_end_to_end_and_is_traceable():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_demo.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "demo: PASS" in result.stdout
    assert "Gate status: untouched" in result.stdout

    build = ROOT / "examples" / "toy_demo" / "build"
    manifest = json.loads((build / "figures" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["figures"]) == 1
    figure = manifest["figures"][0]
    run_dir = build / "runs" / figure["run_id"]
    record = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert record["metrics"]["exit_code"] == 0
    assert record["code_hashes"]

    metrics = json.loads((run_dir / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
    fragment = (build / "paper" / "fragment.md").read_text(encoding="utf-8")
    assert str(metrics["rmse"]) in fragment
    assert str(metrics["k"]) in fragment


def test_demo_check_only_reuses_the_existing_build():
    from scripts.run_demo import BUILD

    if not (BUILD / "paper" / "claim_registry.jsonl").is_file():
        pytest.skip("demo build not present")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_demo.py"), "--check-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "demo check: PASS" in result.stdout


def test_demo_writes_only_inside_its_own_build_directory():
    from scripts.run_demo import BUILD, DEMO

    assert BUILD.parent == DEMO
    assert DEMO == ROOT / "examples" / "toy_demo"


def test_demo_dataset_is_synthetic_and_deterministic():
    from scripts.make_demo_data import series

    rows = series()
    assert len(rows) == 24
    assert rows[0][0] == 0.0
    assert all(y > 0 for _, y in rows)
    assert series() == rows, "the demo fixture must be byte-stable across calls"
