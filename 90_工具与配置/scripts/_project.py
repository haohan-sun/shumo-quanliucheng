from __future__ import annotations

import hashlib
import json
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = ROOT / "90_工具与配置"
WORK_ROOT = ROOT / "03_建模工作区"
PAPER_ROOT = ROOT / "04_论文与提交"
INPUT_ROOT = ROOT / "01_题目与要求"
REFERENCE_ROOT = ROOT / "02_参考文献"
LAYOUT_PATH = TOOLS_ROOT / "configs" / "workspace-layout.yaml"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def load_yaml(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_layout(root: Path = ROOT) -> dict[str, Any]:
    path = root / "90_工具与配置" / "configs" / "workspace-layout.yaml"
    if not path.is_file():
        return {
            "schema_version": "1.0",
            "workspace_root": ".",
            "tool_root": "90_工具与配置",
            "work_root": "03_建模工作区",
            "paper_root": "04_论文与提交",
            "sources": {
                "problem_roots": [],
                "literature_roots": [],
                "requirement_files": [],
            },
            "ignore_name_globs": ["~$*"],
        }
    return load_yaml(path)


def workspace_root(root: Path = ROOT) -> Path:
    layout = load_layout(root)
    return (root / str(layout.get("workspace_root", "."))).resolve()


def tools_root(root: Path = ROOT) -> Path:
    layout = load_layout(root)
    return (root / str(layout.get("tool_root", "90_工具与配置"))).resolve()


def work_root(root: Path = ROOT) -> Path:
    layout = load_layout(root)
    return (root / str(layout.get("work_root", "03_建模工作区"))).resolve()


def paper_root(root: Path = ROOT) -> Path:
    layout = load_layout(root)
    return (root / str(layout.get("paper_root", "04_论文与提交"))).resolve()


def _ignored(path: Path, layout: dict[str, Any]) -> bool:
    return path.name.startswith(".") or any(
        fnmatch(path.name, pattern) for pattern in layout.get("ignore_name_globs", [])
    )


def _configured_paths(kind: str, root: Path = ROOT) -> list[Path]:
    layout = load_layout(root)
    workspace = workspace_root(root)
    return [workspace / str(relative) for relative in layout.get("sources", {}).get(kind, [])]


def _files_from_sources(paths: list[Path], layout: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and not _ignored(path, layout):
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and not _ignored(candidate, layout)
            )
    return files


def iter_input_files(root: Path = ROOT) -> list[Path]:
    layout = load_layout(root)
    files: list[Path] = []
    candidates = [
        work_root(root) / "problem",
        work_root(root) / "data" / "raw",
        # Backward-compatible fallbacks keep isolated unit tests and imported old workspaces valid.
        root / "problem",
        root / "data" / "raw",
    ]
    for base in candidates:
        if not base.exists():
            continue
        files.extend(
            path
            for path in base.rglob("*")
            if path.is_file() and not _ignored(path, layout) and ".downloads" not in path.parts
        )
    files.extend(_files_from_sources(_configured_paths("problem_roots", root), layout))
    files.extend(_files_from_sources(_configured_paths("requirement_files", root), layout))
    unique = {path.resolve(): path for path in files}
    return sorted(unique.values(), key=lambda path: source_key(path, root))


def iter_literature_files(root: Path = ROOT) -> list[Path]:
    layout = load_layout(root)
    files = _files_from_sources(_configured_paths("literature_roots", root), layout)
    unique = {path.resolve(): path for path in files}
    return sorted(unique.values(), key=lambda path: source_key(path, root))


def requirement_files(root: Path = ROOT) -> list[Path]:
    layout = load_layout(root)
    return sorted(
        _files_from_sources(_configured_paths("requirement_files", root), layout),
        key=lambda path: source_key(path, root),
    )


def source_key(path: Path, root: Path = ROOT) -> str:
    workspace = workspace_root(root)
    try:
        return path.resolve().relative_to(workspace).as_posix()
    except ValueError:
        return path.resolve().relative_to(root.resolve()).as_posix()


def input_hashes(root: Path = ROOT) -> dict[str, str]:
    return {source_key(path, root): sha256_file(path) for path in iter_input_files(root)}


def validate_layout(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    layout = load_layout(root)
    if layout.get("schema_version") != "1.0":
        errors.append("90_工具与配置/configs/workspace-layout.yaml: schema_version must be 1.0")
    workspace = workspace_root(root)
    if not workspace.is_dir():
        errors.append(f"configured workspace_root is missing: {workspace}")
        return errors
    configured_tool = tools_root(root)
    configured_work = work_root(root)
    configured_paper = paper_root(root)
    for label, path in (
        ("tool_root", configured_tool),
        ("work_root", configured_work),
        ("paper_root", configured_paper),
    ):
        try:
            path.relative_to(root.resolve())
        except ValueError:
            errors.append(f"configured {label} escapes workspace: {path}")
            continue
        if not path.is_dir():
            errors.append(f"configured {label} is missing: {path}")
    for kind in ("problem_roots", "literature_roots", "requirement_files"):
        for path in _configured_paths(kind, root):
            try:
                path.resolve().relative_to(workspace)
            except ValueError:
                errors.append(f"configured {kind} path escapes workspace: {path}")
                continue
            if not path.exists():
                errors.append(f"configured {kind} path is missing: {path}")
    return errors


def model_status(text: str) -> str | None:
    match = re.search(r"^Status:\s*`?([A-Z_]+)`?\s*$", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def within_root(path: Path, root: Path = ROOT) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
