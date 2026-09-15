from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import PAPER_ROOT, ROOT, load_yaml, paper_root

CATEGORY_LABELS = {
    "literature_public_research": "文献和公开资料检索",
    "program_implementation_debugging": "程序实现与调试",
    "numerical_experiments_optimization": "数值实验与优化",
    "scientific_visualization": "科学可视化",
    "results_paper_review": "结果与论文审核",
    "writing_typesetting": "必要的文字和排版辅助",
}
REQUIRED_FIELDS = {
    "usage_id",
    "date",
    "category",
    "tool_model",
    "stage",
    "purpose",
    "representative_prompts",
    "response_summary",
    "adopted",
    "human_verification",
}
HUMAN_AUTHORITY = (
    "核心问题分析、模型假设、变量定义、目标函数、约束条件、最终模型选择和主要结果解释"
    "由参赛队员独立完成并承担最终责任。"
)


def validate_ledger(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if ledger.get("schema_version") != "1.0":
        errors.append("ledger schema_version must be 1.0")
    ids: set[str] = set()
    for index, record in enumerate(ledger.get("records", [])):
        missing = REQUIRED_FIELDS - set(record)
        if missing:
            errors.append(f"record {index} missing: {', '.join(sorted(missing))}")
            continue
        if record["usage_id"] in ids:
            errors.append(f"duplicate usage_id: {record['usage_id']}")
        ids.add(record["usage_id"])
        if record["category"] not in CATEGORY_LABELS:
            errors.append(f"record {record['usage_id']} has unknown category: {record['category']}")
        prompts = record["representative_prompts"]
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 2:
            errors.append(f"record {record['usage_id']} must contain 1-2 representative prompts")
    categories = {record.get("category") for record in ledger.get("records", [])}
    if len(categories) > 7:
        errors.append("submission report may contain at most 7 categories")
    return errors


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_internal(records: list[dict[str, Any]]) -> str:
    lines = [
        "# AI Usage Internal Ledger",
        "",
        "This generated view contains material AI assistance only. "
        "The structured source is `ledger.yaml`.",
        "",
        HUMAN_AUTHORITY,
        "",
        "| ID | Date | Category | Tool/model | Stage | Purpose | Representative prompt(s) | "
        "Response summary | Adopted | Human verification |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        prompts = "<br>".join(_escape(prompt) for prompt in record["representative_prompts"])
        values = [
            record["usage_id"],
            record["date"],
            CATEGORY_LABELS[record["category"]],
            record["tool_model"],
            record["stage"],
            record["purpose"],
            prompts,
            record["response_summary"],
            "yes" if record["adopted"] else "no",
            record["human_verification"],
        ]
        lines.append("| " + " | ".join(_escape(value) for value in values) + " |")
    if not records:
        lines.append("| — | — | — | — | — | No material AI use recorded. | — | — | — | — |")
    return "\n".join(lines) + "\n"


def render_submission(records: list[dict[str, Any]]) -> str:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for category in CATEGORY_LABELS:
        selected = [record for record in records if record["category"] == category]
        if selected:
            grouped[category] = selected
    lines = [
        "# AI Usage Submission Report",
        "",
        HUMAN_AUTHORITY,
        "",
    ]
    if not grouped:
        lines.extend(["No material AI assistance has been recorded.", ""])
        return "\n".join(lines)
    for number, (category, category_records) in enumerate(grouped.items(), start=1):
        prompts: list[str] = []
        for record in category_records:
            for prompt in record["representative_prompts"]:
                if prompt not in prompts and len(prompts) < 2:
                    prompts.append(prompt)
        tools = sorted({record["tool_model"] for record in category_records})
        purposes = "; ".join(dict.fromkeys(record["purpose"] for record in category_records))
        summaries = "; ".join(
            dict.fromkeys(record["response_summary"] for record in category_records)
        )
        adopted = any(record["adopted"] for record in category_records)
        checks = "; ".join(
            dict.fromkeys(record["human_verification"] for record in category_records)
        )
        lines.extend(
            [
                f"## {number}. {CATEGORY_LABELS[category]}",
                "",
                f"- 工具和模型：{', '.join(tools)}",
                f"- 使用环节与目的：{purposes}",
                f"- 代表性 Prompt：{' / '.join(prompts)}",
                f"- 回复摘要：{summaries}",
                f"- 是否采用：{'是' if adopted else '否'}",
                f"- 人工检查和修改：{checks}",
                "",
            ]
        )
    return "\n".join(lines)


def build(root: Path = ROOT, check: bool = False) -> list[str]:
    papers = PAPER_ROOT if root == ROOT else paper_root(root)
    ledger = load_yaml(papers / "ai_provenance" / "ledger.yaml")
    errors = validate_ledger(ledger)
    if errors:
        return errors
    expected = {
        papers / "ai_provenance" / "AI_USAGE_INTERNAL.md": render_internal(ledger["records"]),
        papers / "ai_provenance" / "AI_USAGE_SUBMISSION.md": render_submission(
            ledger["records"]
        ),
    }
    for path, content in expected.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                relative = path.relative_to(root).as_posix()
                errors.append(f"stale or missing generated report: {relative}")
        else:
            path.write_text(content, encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build internal and submission AI-use reports.")
    parser.add_argument(
        "--check", action="store_true", help="Verify generated reports are current."
    )
    args = parser.parse_args()
    errors = build(check=args.check)
    if errors:
        print("ai usage report: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("ai usage report: PASS" if args.check else "ai usage report: BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
