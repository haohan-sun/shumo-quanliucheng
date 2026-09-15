"""Error registry: cross-run error learning with category-scoped (progressive) loading.

Errors are appended to 90_工具与配置/state/error_registry.jsonl. New tasks query
only the relevant categories — the full history never enters context at once.

CLI:
    python .../error_registry.py --record --category data --summary "..." --lesson "..." --source run|audit --ref <id>
    python .../error_registry.py --query data,assumption --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
REGISTRY_PATH = STATE_DIR / "error_registry.jsonl"

CATEGORIES = (
    "problem_parse", "evidence", "citation", "data", "assumption", "math", "solver",
    "implementation", "numerical", "validation", "visual", "paper", "compliance",
    "reproducibility", "routing", "context",
)
SEVERITIES = ("info", "minor", "major", "critical")


def record_error(
    category: str,
    summary: str,
    lesson: str,
    *,
    severity: str = "major",
    source: str = "audit",
    ref: str = "",
    stage: str = "",
    path: Path = REGISTRY_PATH,
) -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}; choose from {CATEGORIES}")
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity {severity!r}")
    entry = {
        "error_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "category": category,
        "severity": severity,
        "summary": summary,
        "lesson": lesson,
        "source": source,
        "ref": ref,
        "stage": stage,
        "status": "open",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def query_errors(
    categories: list[str] | None = None,
    *,
    limit: int = 5,
    status: str = "any",
    path: Path = REGISTRY_PATH,
) -> list[dict]:
    """Return the most recent errors for the requested categories only."""
    if not path.is_file():
        return []
    wanted = set(categories or CATEGORIES)
    hits: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            if entry["category"] in wanted and status in {"any", entry["status"]}:
                hits.append(entry)
    hits.reverse()  # newest first
    return hits[: max(0, limit)]


def resolve(error_id: str, *, path: Path = REGISTRY_PATH) -> bool:
    """Mark an error resolved in place (lessons stay for future tasks)."""
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        entry = json.loads(line)
        if entry["error_id"] == error_id and entry["status"] == "open":
            entry["status"] = "resolved"
            entry["resolved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            lines[index] = json.dumps(entry, ensure_ascii=False)
            changed = True
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Error registry: record or query lessons.")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--query", metavar="CATS", help="comma-separated categories")
    parser.add_argument("--category")
    parser.add_argument("--summary")
    parser.add_argument("--lesson")
    parser.add_argument("--severity", default="major")
    parser.add_argument("--source", default="audit")
    parser.add_argument("--ref", default="")
    parser.add_argument("--stage", default="")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.record:
        entry = record_error(
            args.category or "", args.summary or "", args.lesson or "",
            severity=args.severity, source=args.source, ref=args.ref, stage=args.stage,
        )
        print(json.dumps(entry, ensure_ascii=False))
        return 0
    cats = [c.strip() for c in args.query.split(",")] if args.query else None
    print(json.dumps(query_errors(cats, limit=args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
