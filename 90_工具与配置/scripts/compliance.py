from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import (
    PAPER_ROOT,
    ROOT,
    TOOLS_ROOT,
    dump_json,
    load_json,
    load_yaml,
    paper_root,
    tools_root,
    within_root,
)


def _finding(level: str, code: str, message: str, evidence: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message, "evidence": evidence}


def collect_findings(root: Path = ROOT, submission: bool = False) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    tools = TOOLS_ROOT if root == ROOT else tools_root(root)
    papers = PAPER_ROOT if root == ROOT else paper_root(root)
    config = load_yaml(tools / "configs" / "contest.yaml")
    strict_level = "BLOCKER" if submission else "WARNING"

    if not config.get("contest"):
        findings.append(
            _finding(
                strict_level,
                "CONTEST_UNASSIGNED",
                "Contest identity and year have not been configured.",
                "90_工具与配置/configs/contest.yaml",
            )
        )
    if not config.get("official_rules_locator"):
        findings.append(
            _finding(
                strict_level,
                "RULES_MISSING",
                "No official contest-rule locator has been recorded; "
                "rule-specific checks cannot be claimed.",
                "90_工具与配置/configs/contest.yaml",
            )
        )
    if submission and not config.get("control_number"):
        findings.append(
            _finding(
                "BLOCKER",
                "CONTROL_NUMBER_MISSING",
                "A control number is required before a submission package can be built.",
                "90_工具与配置/configs/contest.yaml",
            )
        )

    paper_pdf = config.get("paper_pdf")
    if paper_pdf:
        paper_path = root / paper_pdf
        if not within_root(paper_path, root) or not paper_path.is_file():
            findings.append(
                _finding(
                    "BLOCKER" if submission else "WARNING",
                    "PAPER_PDF_MISSING",
                    "Configured paper PDF is missing or outside the workspace.",
                    str(paper_pdf),
                )
            )
        elif config.get("file_size_limit_mb"):
            size_mb = paper_path.stat().st_size / (1024 * 1024)
            if size_mb > float(config["file_size_limit_mb"]):
                findings.append(
                    _finding(
                        "BLOCKER",
                        "PAPER_TOO_LARGE",
                        f"Paper PDF is {size_mb:.2f} MB, above the configured limit.",
                        str(paper_pdf),
                    )
                )
        if paper_path.is_file() and within_root(paper_path, root):
            filename_pattern = config.get("required_filename_pattern")
            if filename_pattern and not re.fullmatch(filename_pattern, paper_path.name):
                findings.append(
                    _finding(
                        "BLOCKER",
                        "FILENAME_RULE_FAILED",
                        "Paper filename does not match the configured official pattern.",
                        str(paper_pdf),
                    )
                )
            try:
                from pypdf import PdfReader

                reader = PdfReader(paper_path)
                page_limit = config.get("page_limit")
                if page_limit is not None and len(reader.pages) > int(page_limit):
                    findings.append(
                        _finding(
                            "BLOCKER",
                            "PAGE_LIMIT_EXCEEDED",
                            f"Paper has {len(reader.pages)} pages; limit is {page_limit}.",
                            str(paper_pdf),
                        )
                    )
                metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
                if config.get("anonymous_submission") and metadata.get("/Author", "").strip():
                    findings.append(
                        _finding(
                            "BLOCKER",
                            "PDF_AUTHOR_METADATA",
                            "Anonymous paper contains a non-empty PDF Author field.",
                            str(paper_pdf),
                        )
                    )
                searchable = " ".join([str(paper_pdf), *metadata.values()]).casefold()
                for term in config.get("forbidden_identity_terms", []):
                    if str(term).casefold() in searchable:
                        findings.append(
                            _finding(
                                "BLOCKER",
                                "IDENTITY_TERM_FOUND",
                                f"Forbidden identity term found in PDF path or metadata: {term}",
                                str(paper_pdf),
                            )
                        )
            except ImportError:
                findings.append(
                    _finding(
                        "BLOCKER" if submission else "WARNING",
                        "PDF_INSPECTOR_MISSING",
                        "Install the document extra to inspect PDF pages and metadata.",
                        "pyproject.toml[project.optional-dependencies.document]",
                    )
                )
            except Exception as exc:
                findings.append(
                    _finding(
                        "BLOCKER",
                        "PDF_INSPECTION_FAILED",
                        f"Paper PDF could not be inspected: {type(exc).__name__}: {exc}",
                        str(paper_pdf),
                    )
                )
    elif submission:
        findings.append(
            _finding(
                "BLOCKER",
                "PAPER_PDF_UNSET",
                "No submission PDF has been configured.",
                "90_工具与配置/configs/contest.yaml",
            )
        )

    verification = load_json(tools / "reports" / "verify.json")
    if submission and verification.get("status") != "verified":
        findings.append(
            _finding(
                "BLOCKER",
                "INDEPENDENT_VERIFICATION_PENDING",
                "Independent final verification is not complete.",
                "90_工具与配置/reports/verify.json",
            )
        )

    if submission and not (papers / "ai_provenance" / "AI_USAGE_SUBMISSION.md").is_file():
        findings.append(
            _finding(
                "BLOCKER",
                "AI_DISCLOSURE_MISSING",
                "The generated submission AI-use report is missing.",
                "04_论文与提交/ai_provenance/AI_USAGE_SUBMISSION.md",
            )
        )

    for relative in config.get("required_supporting_paths", []):
        supporting_path = root / relative
        if not within_root(supporting_path, root) or not supporting_path.exists():
            findings.append(
                _finding(
                    "BLOCKER" if submission else "WARNING",
                    "SUPPORTING_MATERIAL_MISSING",
                    "Configured supporting material is missing or outside the workspace.",
                    str(relative),
                )
            )

    if not findings:
        findings.append(
            _finding(
                "INFO", "NO_FINDINGS", "No configured compliance issue was found.", "workspace"
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rule-backed competition compliance checks.")
    parser.add_argument(
        "--submission", action="store_true", help="Treat readiness gaps as blockers."
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write reports/compliance.json.")
    args = parser.parse_args()
    findings = collect_findings(submission=args.submission)
    payload: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "mode": "submission" if args.submission else "bootstrap",
        "findings": findings,
    }
    if args.write:
        dump_json(TOOLS_ROOT / "reports" / "compliance.json", payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(f"{finding['level']} {finding['code']}: {finding['message']}")
    return 1 if any(item["level"] == "BLOCKER" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
