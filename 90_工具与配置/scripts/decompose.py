#!/usr/bin/env python3
"""Lightweight task decomposition in front of the deterministic router.

A mixed natural-language request such as

    "审计这批数据的缺失值并检验稳健性，同时出一张主结果图和摘要初稿"

contains several atomic tasks.  The existing router deliberately returns exactly
one primary functional Skill per request (see ``auto-routing.yaml``), so without
a decomposition layer one part of the request silently loses its Skill.

This module adds one thin layer:

    complex request -> atomic tasks -> route each with the SAME deterministic
    ``route_task()`` -> dependency DAG -> writer-scope conflict check

Hard invariants (enforced here and covered by tests):

* ``route_task()`` is unchanged and remains the only router; this module never
  picks a Skill by itself.
* A simple request (no two distinct atomic tasks) bypasses decomposition and
  returns the single router decision untouched.
* Decomposition never approves, skips, or reorders a Human Gate.  A task that
  routes to a Gate is reported as a stop point, and anything whose stage is later
  than an unapproved Gate is marked ``blocked_prerequisite``.
* No two tasks declare the same writer scope without a dependency path ordering
  them; a genuine conflict is reported as an error, not silently serialised.
* Tasks whose stage is earlier than an approved downstream Gate must be recorded,
  never auto-executed around the Gate.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, load_json
from scripts.auto_route import EXPECTED_GATES, RouteDecision, route_task

# ---------------------------------------------------------------------------
# Atomic task classes.  ``step`` is the canonical workflow position; it is used
# only to order dependencies, never to skip a Human Gate.
# ---------------------------------------------------------------------------
TASK_CLASSES: tuple[tuple[str, int, str, tuple[str, ...]], ...] = (
    ("evidence", 1, "inputs, attachments, data facts, parameter evidence", ()),
    ("literature", 1, "literature, paper search, citation, novelty", ()),
    ("problem", 2, "problem decomposition, units, assumptions, requirements", ()),
    ("data", 2, "data quality, leakage, preprocessing contract", ()),
    ("route", 3, "candidate modeling routes compared under one rubric", ()),
    ("derivation", 4, "mathematical derivation of the selected route", ()),
    ("model_spec", 5, "authoritative MODEL_SPEC and change control", ()),
    ("solver", 6, "solver portfolio for the frozen model", ()),
    ("implementation", 7, "implementation of the frozen MODEL_SPEC / baseline", ()),
    ("experiment", 9, "parameter search, solver comparison, ablation, benchmark", ()),
    ("validation", 9, "validation, uncertainty, calibration, robustness", ()),
    ("reproducibility", 10, "run provenance and replication of important numbers", ()),
    ("figure", 11, "figures rendered from registered results", ()),
    ("audit", 12, "result consistency, bug, validity, reproducibility audit", ()),
    ("paper", 12, "paper drafting or polishing from registered evidence", ()),
    ("defense", 13, "cross-artifact manuscript/defense consistency audit", ()),
    ("compliance", 14, "submission, anonymity, AI disclosure", ()),
    ("provenance", 15, "material AI-use recording and reporting", ()),
)

# Detection patterns.  They mirror the English terms the authoritative router uses
# in ``configs/auto-routing.yaml`` (plus common Chinese phrasings) so that a class
# decision here and the router's own decision agree.  Longest-match wins, then
# canonical step order decides.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "evidence": (
        "附件", "数据事实", "参数依据", "检索输入", "证据",
        "data evidence", "parameter source", "attachment", "dataset",
    ),
    "literature": (
        "文献", "引用", "参考文献", "查新", "检索论文",
        "literature", "paper search", "citation", "novelty", "doi",
    ),
    "problem": (
        "拆解题目", "拆题", "问题分析", "问题拆解", "目标函数", "约束条件",
        "假设", "假设账本", "量纲", "量纲分析", "单位", "重述",
        "problem decomposition", "problem analysis", "assumption ledger",
    ),
    "data": (
        "数据审计", "数据质量", "缺失", "缺失值", "异常值", "离群", "泄漏",
        "标签泄漏", "预处理", "字段",
        "data audit", "data quality", "missing values", "label leakage",
    ),
    "route": (
        "路线比较", "候选路线", "候选建模路线", "路线选择", "方案比较",
        "candidate route", "candidate modeling route", "compare methods", "route tree",
    ),
    "derivation": (
        "推导", "数学推导", "建模推导", "方程推导", "边界条件", "极限情形", "数学表达",
        "mathematical derivation", "derive equations",
        "assumption to equation", "dimensional consistency",
    ),
    "model_spec": (
        "model_spec", "模型规格", "规格冻结", "冻结规格",
        "model spec", "check model spec", "equation check", "constraint check",
    ),
    "solver": ("求解器", "求解策略", "solver strategy", "solver portfolio", "solver availability"),
    "implementation": (
        "实现代码", "写代码", "实现基线", "基线实现", "编码实现", "复现该模型",
        "implement approved model", "approved model code", "baseline code",
    ),
    "experiment": (
        "调参", "参数搜索", "参数调优", "消融", "基准测试", "性能基准", "对比实验",
        "optimization", "parameter tuning", "hyperparameter search",
        "solver comparison", "ablation", "performance benchmark",
    ),
    "validation": (
        "稳健性", "鲁棒性", "敏感性", "灵敏度", "不确定性", "标定", "泛化", "残差",
        "压力情景",
        "model validation", "sensitivity analysis", "robustness validation",
        "uncertainty quantification", "calibration", "stress test",
        "seed robustness", "generalization",
    ),
    "reproducibility": (
        "可复现", "复现运行", "运行记录", "哈希",
        "reproducibility", "replicate run", "run record", "reproduction command",
    ),
    "figure": (
        "画图", "绘图", "制图", "出图", "成图", "结果图", "主结果图", "示意图",
        "图表", "图片", "图形", "可视化",
        "figure", "plot", "chart", "visual design",
    ),
    "audit": (
        "审计结果", "结果审计", "复核结果", "一致性问题", "结果是否可", "审查结果",
        "audit result", "consistency", "result validity",
    ),
    "paper": (
        "论文", "摘要", "正文", "写作", "润色", "改写",
        "write paper", "draft abstract", "polish manuscript", "paper writing",
    ),
    "defense": (
        "答辩", "答辩问题", "交叉审查",
        "defense", "paper audit", "claim consistency",
    ),
    "compliance": (
        "提交检查", "匿名", "控制号", "合规", "格式检查", "文件限制",
        "submission", "anonymity", "control number", "ai disclosure",
    ),
    "provenance": ("ai 使用", "使用记录", "披露", "ai provenance", "ai usage"),
}

# Writers own disjoint artifact classes.  Two tasks may only share a scope when a
# dependency path already orders them.
WRITER_SCOPES: dict[str, str] = {
    "deriver": "03_建模工作区/model/MODEL_DERIVATION.md",
    "implementer": "03_建模工作区/src/**",
    "optimizer": "03_建模工作区/experiments/**",
    "visualizer": "03_建模工作区/figures/**",
}

# Clause connectors only.  Punctuation is deliberately excluded: the ideographic
# comma "、" and the ASCII comma both join items inside one task ("变量、单位和约束"),
# so splitting on them would fragment a single request into meaningless pieces.
# ASCII connectors carry surrounding spaces so they cannot match inside a word.
COORDINATORS = (
    "并且",
    "同时",
    "然后",
    "接着",
    "随后",
    "以及",
    "；",
    ";",
    " and ",
    " then ",
    " plus ",
)
_ASCII_COORDINATORS = tuple(item for item in COORDINATORS if item.isascii())


@dataclass
class DecomposedTask:
    """One atomic task plus the untouched router decision that governs it."""

    task_id: str
    text: str
    task_class: str
    step: int
    decision: RouteDecision
    depends_on: list[str] = field(default_factory=list)
    writer_scope: str | None = None
    same_artifact_slot: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = {
            "task_id": self.task_id,
            "text": self.text,
            "task_class": self.task_class,
            "step": self.step,
            "action": self.decision.action,
            "primary_skill": self.decision.primary_skill,
            "agents": list(self.decision.agents),
            "review_agents": list(self.decision.review_agents),
            "depends_on": list(self.depends_on),
            "writer_scope": self.writer_scope,
            "same_artifact_slot": self.same_artifact_slot,
            "gate": self.decision.gate,
            "missing_gates": list(self.decision.missing_gates),
            "reason_codes": list(self.decision.reason_codes),
        }
        return payload


def _split_segments(request: str) -> list[str]:
    """Split a request into candidate clauses on explicit coordinators.

    An ASCII coordinator such as ``" and "`` carries surrounding spaces so it
    cannot match inside a word; those spaces are consumed by the split, so they
    are put back to keep the neighbouring words from fusing together.
    """
    pattern = "(" + "|".join(re.escape(token) for token in COORDINATORS) + ")"
    pieces = re.split(pattern, request)
    segments: list[str] = []
    for index, piece in enumerate(pieces):
        if index % 2 == 1:  # the separator itself
            continue
        if not piece.strip():
            continue
        text = piece
        if index > 0:
            text = " " + text
        if index < len(pieces) - 1:
            text = text + " "
        stripped = text.strip()
        # A leading/trailing ASCII connector is a separator, not part of the clause.
        for token in _ASCII_COORDINATORS:
            bare = token.strip()
            if stripped.casefold().startswith(bare + " "):
                stripped = stripped[len(bare):].strip()
            if stripped.casefold().endswith(" " + bare):
                stripped = stripped[: -len(bare)].strip()
        if stripped:
            segments.append(stripped)
    return segments


def classify(segment: str) -> str | None:
    """Return the task class for a clause, or ``None`` when nothing matches."""
    folded = segment.casefold()
    matches: list[tuple[int, int, str]] = []
    for index, (task_class, _step, _intent, _extra) in enumerate(TASK_CLASSES):
        for keyword in KEYWORDS[task_class]:
            position = folded.find(keyword.casefold())
            if position >= 0:
                matches.append((len(keyword), -index, task_class))
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][2]


def _step_of(task_class: str) -> int:
    for name, step, _intent, _extra in TASK_CLASSES:
        if name == task_class:
            return step
    raise KeyError(task_class)


def _intent_of(task_class: str) -> str:
    for name, _step, intent, _extra in TASK_CLASSES:
        if name == task_class:
            return intent
    raise KeyError(task_class)


def atomic_tasks(request: str) -> list[tuple[str | None, str]]:
    """Return ``[(task_class_or_None, clause_text), ...]``, deduplicated and ordered.

    ``None`` means the clause matched no curated keyword.  Such a clause is kept
    and handed to the router verbatim: dropping it would silently lose part of the
    user's request, which is exactly the failure decomposition exists to avoid.
    """
    found: list[tuple[int, str, str | None]] = []
    seen: set[str] = set()
    for clause in _split_segments(request):
        task_class = classify(clause)
        key = task_class or clause.casefold()
        if key in seen:
            continue
        seen.add(key)
        step = _step_of(task_class) if task_class else len(TASK_CLASSES) + 1
        found.append((step, clause, task_class))
    if not found:
        return [(classify(request), request.strip())]
    found.sort(key=lambda item: (item[0], item[2] or "~"))
    return [(task_class, clause) for _step, clause, task_class in found]


def _route_for(
    task_class: str | None, clause: str, manifest: dict | None, root: Path
) -> RouteDecision:
    """Route one atomic task with the project's unchanged deterministic router.

    A classified clause is routed by its canonical intent text (exactly how the
    router is driven today).  An unclassified clause is routed verbatim so the
    router's own fallback logic decides, and the clause is never silently dropped.

    ``RouteDecision`` is a frozen dataclass, so the annotation is attached with
    ``dataclasses.replace`` rather than by mutating the router's return value.
    """
    if task_class is None:
        decision = route_task(clause, manifest, project_related=True, root=root)
        extra = "task_decomposition: clause had no curated keyword; routed verbatim"
    else:
        intent = _intent_of(task_class)
        decision = route_task(intent, manifest, project_related=True, root=root)
        if not clause.strip() or clause.strip() == intent:
            return decision
        extra = "task_decomposition: clause mapped to its canonical routed intent"
    return replace(decision, reason_codes=[*decision.reason_codes, extra])


def _gate_index(gate: str | None) -> int:
    if not gate:
        return len(EXPECTED_GATES)
    return EXPECTED_GATES.index(gate) if gate in EXPECTED_GATES else len(EXPECTED_GATES)


def plan_request(
    request: str,
    manifest: dict | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, object]:
    """Decompose a request into a routed, dependency-ordered task plan."""
    if manifest is None:
        manifest_path = root / "run-manifest.json"
        manifest = load_json(manifest_path) if manifest_path.is_file() else {}

    atoms = atomic_tasks(request)
    # A clause with no curated keyword is routed verbatim, which can legitimately
    # end in the router's own single-task fallback.  Those requests keep the
    # original one-decision behaviour instead of being reported as a plan.
    unclassified = [clause for task_class, clause in atoms if task_class is None]
    if len(atoms) < 2 or len(unclassified) == len(atoms):
        # Simple request: keep the existing single-task routing behaviour.
        decision = route_task(request, manifest, project_related=True, root=root)
        return {
            "decomposed": False,
            "request": request,
            "reason": (
                "no curated keyword matched; deterministic router result returned unchanged"
                if unclassified
                else "single atomic task; deterministic router result returned unchanged"
            ),
            "tasks": [],
            "single_decision": decision.to_dict(),
            "execution_waves": [[decision.primary_skill]] if decision.primary_skill else [],
            "gate_stops": [decision.gate] if decision.gate else [],
            "blocked_prerequisite": [],
            "errors": [],
        }

    counts: dict[str, int] = {}
    tasks: list[DecomposedTask] = []
    for task_class, clause in atoms:
        label = task_class or "unclassified"
        counts[label] = counts.get(label, 0) + 1
        step = _step_of(task_class) if task_class else len(TASK_CLASSES) + 1
        tasks.append(
            DecomposedTask(
                task_id=f"T{len(tasks) + 1}",
                text=clause,
                task_class=label,
                step=step,
                decision=_route_for(task_class, clause, manifest, root),
            )
        )

    # A dependency edge is only added when the earlier task is an artefact
    # producer for the later one; ordering is by canonical step, so the graph is
    # acyclic by construction and same-step tasks stay parallel.
    for task in tasks:
        earlier = [other for other in tasks if other.step < task.step]
        if earlier:
            task.depends_on = [max(earlier, key=lambda item: item.step).task_id]

    errors: list[str] = []
    for task in tasks:
        writer = next(
            (agent for agent in task.decision.agents if agent in WRITER_SCOPES),
            None,
        )
        task.writer_scope = WRITER_SCOPES[writer] if writer else None

    by_scope: dict[str, list[DecomposedTask]] = {}
    for task in tasks:
        if task.writer_scope:
            by_scope.setdefault(task.writer_scope, []).append(task)
            task.same_artifact_slot = task.step in {3, 12}
    for scope, owners in by_scope.items():
        if len(owners) < 2:
            continue
        ordered = _has_path(tasks, owners[0].task_id, owners[1].task_id) or _has_path(
            tasks, owners[1].task_id, owners[0].task_id
        )
        if not ordered:
            errors.append(
                "writer scope conflict: "
                + ", ".join(f"{item.task_id}({item.text})" for item in owners)
                + f" both write {scope} with no dependency ordering; "
                "assign one writer or split the artifact"
            )

    waves: list[list[str]] = []
    for _step, group in itertools.groupby(sorted(tasks, key=lambda item: item.step), key=lambda i: i.step):
        wave = [item.task_id for item in group]
        if wave:
            waves.append(wave)

    approved = [
        gate
        for gate in EXPECTED_GATES
        if _gate_approved(manifest, gate)
    ]
    gate_stops = sorted(
        [task.decision.gate for task in tasks if task.decision.gate],
        key=_gate_index,
    )
    blocked = [
        {
            "task_id": task.task_id,
            "text": task.text,
            "missing_gates": list(task.decision.missing_gates),
            "action": task.decision.action,
        }
        for task in tasks
        if task.decision.action == "blocked_prerequisite"
    ]

    return {
        "decomposed": True,
        "request": request,
        "reason": f"{len(tasks)} atomic tasks detected",
        "tasks": [task.to_dict() for task in tasks],
        "single_decision": None,
        "execution_waves": waves,
        "approved_gates": approved,
        "gate_stops": list(dict.fromkeys(gate_stops)),
        "blocked_prerequisite": blocked,
        "errors": errors,
        "notes": [
            "Each task's Skill/Agent comes from the unchanged deterministic router.",
            "No Human Gate is approved, skipped or reordered by this plan.",
            "Read-only review agents may run in parallel; writers never share a scope "
            "without dependency ordering.",
        ],
    }


def _gate_approved(manifest: dict, gate: str) -> bool:
    from scripts.auto_route import valid_human_gate

    return valid_human_gate(manifest, gate)


def _has_path(tasks: list[DecomposedTask], start: str, target: str) -> bool:
    graph = {task.task_id: task.depends_on for task in tasks}
    stack = list(graph.get(start, []))
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, []))
    return False


def render(plan: dict[str, object]) -> str:
    lines: list[str] = []
    if not plan["decomposed"]:
        decision = plan["single_decision"]
        lines.append("task plan: single atomic task (no decomposition)")
        lines.append(f"  primary skill : {decision['primary_skill']}")
        lines.append(f"  agents        : {', '.join(decision['agents']) or '-'}")
        lines.append(f"  action        : {decision['action']}")
        if decision.get("gate"):
            lines.append(f"  gate stop     : {decision['gate']} (requires an explicit human decision)")
        return "\n".join(lines)

    lines.append(f"task plan: {plan['reason']}")
    lines.append("")
    lines.append("tasks (dependency-ordered):")
    for task in plan["tasks"]:
        depends = f" after {', '.join(task['depends_on'])}" if task["depends_on"] else ""
        lines.append(
            f"  {task['task_id']} [step {task['step']:>2}] {task['task_class']:<15} "
            f"-> {task['primary_skill'] or '-'}{depends}"
        )
        lines.append(f"        request : {task['text']}")
        if task["agents"]:
            lines.append(f"        writers : {', '.join(task['agents'])}")
        if task["review_agents"]:
            lines.append(f"        review  : {', '.join(task['review_agents'])} (read-only)")
        if task["action"] != "route":
            lines.append(f"        action  : {task['action']}")
    lines.append("")
    lines.append("execution waves (tasks in one wave may run in parallel):")
    for index, wave in enumerate(plan["execution_waves"], 1):
        lines.append(f"  wave {index}: {', '.join(wave)}")
    if plan["gate_stops"]:
        lines.append("")
        lines.append("Human Gate stop points (no automatic approval):")
        for gate in plan["gate_stops"]:
            lines.append(f"  {gate}")
    if plan["blocked_prerequisite"]:
        lines.append("")
        lines.append("blocked by an unapproved prerequisite Gate:")
        for item in plan["blocked_prerequisite"]:
            lines.append(f"  {item['task_id']}: requires {', '.join(item['missing_gates'])}")
    if plan["errors"]:
        lines.append("")
        lines.append("plan errors:")
        for error in plan["errors"]:
            lines.append(f"  - {error}")
    lines.append("")
    for note in plan["notes"]:
        lines.append(f"note: {note}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Decompose a complex request into atomic tasks and route each one with the "
            "deterministic router. Never approves a Human Gate."
        )
    )
    parser.add_argument("request")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan = plan_request(args.request)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render(plan))
    return 1 if plan["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
