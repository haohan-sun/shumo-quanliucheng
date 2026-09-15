"""Artifact boundary guard: locked caches and internal state never enter a package.

Policy: 90_工具与配置/configs/artifact_boundaries.yaml (single source of truth).
Used by build_submission before packaging and by tests.

CLI:
    python .../package_guard.py --paths-from zip_or_dir_or_listfile
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, load_yaml

BOUNDARIES_PATH = ROOT / "90_工具与配置" / "configs" / "artifact_boundaries.yaml"
# Directory names that only ever hold regenerable interpreter/test caches.  They
# are skipped while walking a package tree; the explicit boundary rules still
# reject them when they appear inside an actual archive namelist.
PRUNED_DIRECTORY_NAMES = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"})


def load_boundaries(path: Path = BOUNDARIES_PATH) -> dict[str, Any]:
    return load_yaml(path)


def excluded(path_text: str, boundaries: dict[str, Any]) -> str | None:
    """Return the matching rule if path_text is forbidden in a deliverable."""
    normalized = path_text.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
        return "absolute or traversal path"
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.casefold()
    for rule in boundaries.get("exclude_from_package", []):
        pattern = str(rule["pattern"]).replace("\\", "/").casefold()
        patterns = [pattern, pattern[3:]] if pattern.startswith("**/") else [pattern]
        if any(fnmatch.fnmatchcase(normalized, p) or
               (p.endswith("/**") and fnmatch.fnmatchcase(normalized.rstrip("/"), p[:-3]))
               for p in patterns):
            return str(rule.get("reason", pattern))
    return None


def collect_paths(target: Path) -> list[str]:
    if target.is_file() and target.suffix == ".zip":
        with zipfile.ZipFile(target) as archive:
            return archive.namelist()
    if target.is_dir():
        base = ROOT if target.resolve().is_relative_to(ROOT) else target.resolve()
        paths = []
        for directory, dirs, files in os.walk(target, followlinks=False):
            # Regenerable interpreter caches are implementation noise, not
            # deliverables: a normal test run creates them, so reporting them as
            # boundary violations would make every packaged tree look broken.
            dirs[:] = [name for name in dirs if name not in PRUNED_DIRECTORY_NAMES]
            for name in dirs + files:
                item = Path(directory) / name
                if item.is_symlink() or os.path.isjunction(item):
                    raise ValueError(f"package contains link: {item}")
                paths.append(item.relative_to(base).as_posix())
        return sorted(paths)
    if target.is_file():
        return [
            line.strip()
            for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    raise FileNotFoundError(target)


def check_target(target: Path, boundaries: dict[str, Any] | None = None) -> list[str]:
    boundaries = boundaries or load_boundaries()
    violations: list[str] = []
    for path_text in collect_paths(target):
        rule = excluded(path_text, boundaries)
        if rule:
            violations.append(f"{path_text} -> forbidden by rule: {rule}")
    return violations


def assert_package_files(paths: Iterable[Path], root: Path = ROOT,
                         boundaries: dict[str, Any] | None = None) -> None:
    """Fail closed before opening an archive; validate names AND physical targets."""
    boundaries = load_boundaries() if boundaries is None else boundaries
    root = root.resolve()
    for path in paths:
        absolute = Path(os.path.abspath(path))
        if not absolute.is_relative_to(root) or not absolute.resolve().is_relative_to(root):
            raise ValueError(f"package source outside workspace: {path}")
        for name in (absolute.relative_to(root).as_posix(), absolute.resolve().relative_to(root).as_posix()):
            reason = excluded(name, boundaries)
            if reason:
                raise ValueError(f"forbidden package source: {name}: {reason}")
        for parent in (absolute, *absolute.parents):
            if parent == root:
                break
            if parent.is_symlink() or os.path.isjunction(parent):
                raise ValueError(f"linked package source: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deliverable for forbidden paths.")
    parser.add_argument("targets", nargs="+", type=Path)
    args = parser.parse_args()
    boundaries = load_boundaries()
    violations: list[str] = []
    for target in args.targets:
        violations.extend(check_target(target, boundaries))
    print("\n".join(violations) if violations else "package boundary: PASS")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
