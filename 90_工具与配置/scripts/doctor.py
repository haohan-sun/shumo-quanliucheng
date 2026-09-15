from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, TOOLS_ROOT

REQUIRED_MODULES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "sympy": "sympy",
    "sklearn": "scikit-learn",
    "statsmodels": "statsmodels",
    "matplotlib": "matplotlib",
    "plotly": "plotly",
    "openpyxl": "openpyxl",
    "pyarrow": "pyarrow",
    "networkx": "networkx",
    "pydantic": "pydantic",
    "yaml": "PyYAML",
    "jsonschema": "jsonschema",
    "pandera": "pandera",
    "rich": "rich",
    "tqdm": "tqdm",
    "joblib": "joblib",
    "pytest": "pytest",
    "jupyterlab": "jupyterlab",
    "ipykernel": "ipykernel",
    "kaleido": "kaleido",
}
# ``uv`` is an optional accelerator: setup works with plain pip, so its absence
# must not fail the environment.  Only git and the project's own linter are
# required for the documented workflow.
REQUIRED_COMMANDS = ["git", "ruff"]
OPTIONAL_COMMANDS = ["uv", "pandoc", "pdflatex", "xelatex", "latexmk"]


def _command_path(name: str) -> str | None:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    for relative in (
        Path(".venv") / "Scripts" / f"{name}.exe",
        Path(".venv") / "bin" / name,
    ):
        local = ROOT / relative
        if local.is_file():
            return str(local)
    return None


def inspect_environment() -> dict[str, object]:
    python_ok = (3, 11) <= sys.version_info[:2] < (3, 14)
    expected_venv = (ROOT / ".venv").resolve()
    active_venv = Path(sys.prefix).resolve() == expected_venv
    modules: dict[str, dict[str, object]] = {}
    for module, distribution in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module)
            version = importlib.metadata.version(distribution)
            modules[module] = {"available": True, "version": version}
        except Exception as exc:  # module import errors are environment findings
            modules[module] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

    commands = {
        name: _command_path(name) for name in [*REQUIRED_COMMANDS, *OPTIONAL_COMMANDS]
    }
    required_ok = (
        python_ok
        and active_venv
        and all(commands[name] for name in REQUIRED_COMMANDS)
        and all(entry["available"] for entry in modules.values())
    )
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "required_ok": required_ok,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "supported": python_ok,
            "project_venv_active": active_venv,
        },
        "platform": platform.platform(),
        "modules": modules,
        "commands": commands,
    }


def render_report(report: dict[str, object]) -> str:
    python = report["python"]
    modules = report["modules"]
    commands = report["commands"]
    lines = [
        "# Environment Report",
        "",
        f"- Checked at: `{report['checked_at']}`",
        f"- Required environment: `{'PASS' if report['required_ok'] else 'FAIL'}`",
        f"- Python: `{python['version']}` at `{python['executable']}`",
        f"- Project virtual environment active: `{python['project_venv_active']}`",
        f"- Platform: `{report['platform']}`",
        "",
        "## Required Python modules",
        "",
        "| Module | Available | Version or error |",
        "| --- | --- | --- |",
    ]
    for name, entry in modules.items():
        detail = entry.get("version", entry.get("error", ""))
        lines.append(f"| `{name}` | {entry['available']} | {detail} |")
    lines.extend(
        [
            "",
            "## External commands",
            "",
            "| Command | Path | Requirement |",
            "| --- | --- | --- |",
        ]
    )
    for name, path in commands.items():
        if name in REQUIRED_COMMANDS:
            requirement = "required"
        elif name == "uv":
            requirement = "optional (setup accelerator)"
        else:
            requirement = "optional/later-stage"
        lines.append(f"| `{name}` | `{path or 'MISSING'}` | {requirement} |")
    lines.extend(
        [
            "",
            "Missing `uv` only means setup used pip instead; the workspace is fully "
            "functional without it.",
            "",
            "Missing Pandoc or LaTeX is not a bootstrap blocker, but it blocks the "
            "corresponding paper-rendering path later.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the project runtime and dependencies.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--no-write", action="store_true", help="Do not update the report file.")
    args = parser.parse_args()
    report = inspect_environment()
    if not args.no_write:
        path = TOOLS_ROOT / "reports" / "ENVIRONMENT_REPORT.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_report(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"environment: {'PASS' if report['required_ok'] else 'FAIL'}")
        print(f"report: {TOOLS_ROOT / 'reports' / 'ENVIRONMENT_REPORT.md'}")
    return 0 if report["required_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
