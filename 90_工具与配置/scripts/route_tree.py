"""Route tree: budgeted beam/tree search over candidate modeling routes.

Design (AI-Scientist-v2 / AFlow 思想的轻量化): routes form a tree; each node
carries hypothesis/model/solver/risk/cost; cheap quick-tests score nodes before
any real experiment; beam width and quick-test budget cap exploration; prune
promotes survival only.

CLI:
    python 90_工具与配置/scripts/route_tree.py --stats 03_建模工作区/decisions/route_tree.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_BUDGET = {"max_nodes": 16, "max_depth": 3, "max_quick_tests": 8, "beam_width": 4}


class BudgetExceeded(RuntimeError):
    pass


def new_tree(problem_id: str, budget: dict[str, int] | None = None) -> dict[str, Any]:
    tree = {
        "schema_version": "1.0",
        "problem_id": problem_id,
        "budget": {**DEFAULT_BUDGET, **(budget or {})},
        "used": {"nodes": 0, "quick_tests": 0},
        "nodes": [],
        "promoted_route_id": None,
    }
    validate_tree(tree)
    return tree


def _score(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("score must be finite and between 0 and 1")
    return value


def _state(tree: dict[str, Any], route_id: str, allowed: set[str]) -> dict[str, Any]:
    if tree.get("promoted_route_id"):
        raise ValueError("tree is closed after human G2 selection")
    node = _require(tree, route_id)
    if node["status"] not in allowed:
        raise ValueError(f"invalid lifecycle transition from {node['status']}")
    return node


def _find(tree: dict[str, Any], route_id: str) -> dict[str, Any] | None:
    return next((n for n in tree["nodes"] if n["route_id"] == route_id), None)


def add_route(
    tree: dict[str, Any],
    *,
    hypothesis: str,
    model_family: str,
    solver: str,
    parent: str | None = None,
    expected_score: float = 0.5,
    risk: str = "",
    experiment_cost: float = 1.0,
    **optional: Any,
) -> dict[str, Any]:
    validate_tree(tree)
    if tree.get("promoted_route_id"):
        raise ValueError("tree is closed after human G2 selection")
    expected_score = _score(expected_score)
    if not hypothesis.strip() or not model_family.strip() or not solver.strip():
        raise ValueError("hypothesis, model_family and solver are required")
    if not math.isfinite(experiment_cost) or experiment_cost < 0:
        raise ValueError("experiment_cost must be finite and nonnegative")
    budget = tree["budget"]
    if tree["used"]["nodes"] >= budget["max_nodes"]:
        raise BudgetExceeded("total node budget exhausted; pruning does not refund budget")
    if parent is not None:
        parent_node = _find(tree, parent)
        if parent_node is None:
            raise ValueError(f"unknown parent route: {parent}")
        if parent_node["status"] != "quick_tested" or parent_node not in beam_survivors(tree, parent_node["depth"]):
            raise ValueError("only quick-tested beam survivors may expand")
        depth = parent_node["depth"] + 1
        if depth > budget["max_depth"]:
            raise BudgetExceeded("depth budget exhausted")
    else:
        depth = 0
    node = {
        "route_id": f"R{len(tree['nodes']) + 1:02d}",
        "parent": parent,
        "depth": depth,
        "status": "generated",
        "hypothesis": hypothesis,
        "model_family": model_family,
        "preprocessing": optional.get("preprocessing"),
        "objective": optional.get("objective"),
        "constraints": optional.get("constraints"),
        "solver": solver,
        "complexity": optional.get("complexity"),
        "evidence": list(optional.get("evidence", [])),
        "novelty": optional.get("novelty", "incremental"),
        "expected_score": float(expected_score),
        "quick_test_score": None,
        "risk": risk,
        "failure_condition": optional.get("failure_condition"),
        "experiment_cost": float(experiment_cost),
        "prune_reason": None,
        "children": [],
    }
    if parent is not None:
        parent_node["children"].append(node["route_id"])
    tree["nodes"].append(node)
    tree["used"]["nodes"] += 1
    return node


def record_review(tree: dict[str, Any], route_id: str, risk: str, expected_score: float) -> None:
    expected_score = _score(expected_score)
    node = _state(tree, route_id, {"generated", "revised"})
    node["status"] = "reviewed"
    node["risk"] = risk
    node["expected_score"] = float(expected_score)


def record_quick_test(tree: dict[str, Any], route_id: str, score: float) -> float:
    """Register a cheap empirical probe (e.g., subsample fit) for the route."""
    score = _score(score)
    node = _state(tree, route_id, {"reviewed"})
    if tree["used"]["quick_tests"] >= tree["budget"]["max_quick_tests"]:
        raise BudgetExceeded("quick-test budget exhausted")
    node["quick_test_score"] = float(score)
    node["status"] = "quick_tested"
    tree["used"]["quick_tests"] += 1
    return node["quick_test_score"]


def prune(tree: dict[str, Any], route_id: str, reason: str) -> None:
    node = _state(tree, route_id, {"generated", "reviewed", "quick_tested", "revised"})
    if not reason.strip():
        raise ValueError("prune reason is required")
    node["status"] = "pruned"
    node["prune_reason"] = reason


def revise(tree: dict[str, Any], route_id: str, note: str) -> None:
    node = _state(tree, route_id, {"reviewed", "quick_tested"})
    if not note.strip() or node["children"]:
        raise ValueError("revision needs a note and a leaf node; expanded hypotheses are immutable")
    node["status"] = "revised"
    node["prune_reason"] = None
    node["quick_test_score"] = None
    node["hypothesis"] = f"{node['hypothesis']} [revised: {note}]"


def beam_survivors(tree: dict[str, Any], depth: int) -> list[dict[str, Any]]:
    """Rank tested nodes only; ties use expected score, cost, then stable ID."""
    alive = [
        n
        for n in tree["nodes"]
        if n["depth"] == depth and n["status"] == "quick_tested"
    ]
    alive.sort(
        key=lambda n: (-n["quick_test_score"], -n["expected_score"], n["experiment_cost"], n["route_id"])
    )
    return alive[: tree["budget"]["beam_width"]]


def promote(tree: dict[str, Any], route_id: str, *, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Consume an existing human G2 record; never write or approve a Gate."""
    from scripts.auto_route import gate_records, valid_human_gate

    if not manifest or not valid_human_gate(manifest, "G2"):
        raise PermissionError("human G2 approval is mandatory")
    approval = gate_records(manifest)["G2"]
    if approval.get("route_id") != route_id or approval.get("problem_id") != tree["problem_id"]:
        raise PermissionError("G2 approval must bind this problem_id and route_id")
    if approval.get("route_tree_sha256") != tree_fingerprint(tree):
        raise PermissionError("G2 approval must bind the current route-tree content hash")
    node = _state(tree, route_id, {"quick_tested"})
    node["status"] = "promoted"
    tree["promoted_route_id"] = route_id
    for other in tree["nodes"]:
        if other["route_id"] != route_id and other["status"] not in {"pruned"}:
            other["status"] = "pruned"
            other["prune_reason"] = "lost to promoted route"
    return node


def tree_fingerprint(tree: dict[str, Any]) -> str:
    """Hash the decision evidence before promotion; material candidate edits change it."""
    validate_tree(tree)
    decision = {key: tree[key] for key in ("schema_version", "problem_id", "budget", "used", "nodes")}
    payload = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prune_below_beam(tree: dict[str, Any], depth: int) -> list[str]:
    if tree.get("promoted_route_id"):
        raise ValueError("tree is closed after human G2 selection")
    if any(n["depth"] == depth and n["status"] in {"generated", "reviewed", "revised"} for n in tree["nodes"]):
        raise ValueError("review/test or explicitly prune untested nodes before beam pruning")
    keep = {n["route_id"] for n in beam_survivors(tree, depth)}
    pruned: list[str] = []
    for node in tree["nodes"]:
        if node["depth"] == depth and node["status"] not in {"pruned"} and node["route_id"] not in keep:
            node["status"] = "pruned"
            node["prune_reason"] = f"outside beam at depth {depth}"
            pruned.append(node["route_id"])
    return pruned


def _require(tree: dict[str, Any], route_id: str) -> dict[str, Any]:
    node = _find(tree, route_id)
    if node is None:
        raise ValueError(f"unknown route: {route_id}")
    return node


def load_tree(path: str | Path) -> dict[str, Any]:
    tree = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_tree(tree)
    return tree


def validate_tree(tree: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/route-tree.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(tree)
    nodes = tree["nodes"]
    ids = {n["route_id"] for n in nodes}
    if len(ids) != len(nodes) or tree["used"]["nodes"] != len(nodes):
        raise ValueError("duplicate IDs or inconsistent node counter")
    if len(nodes) > tree["budget"]["max_nodes"] or tree["used"]["quick_tests"] > tree["budget"]["max_quick_tests"]:
        raise BudgetExceeded("stored tree exceeds budget")
    for node in nodes:
        if node["depth"] > tree["budget"]["max_depth"]:
            raise BudgetExceeded("stored tree exceeds depth budget")
        parent = _find(tree, node["parent"]) if node["parent"] else None
        if node["parent"] and (parent is None or node["depth"] != parent["depth"] + 1 or node["route_id"] not in parent["children"]):
            raise ValueError("invalid parent/depth linkage")
        if not node["parent"] and node["depth"] != 0:
            raise ValueError("root depth must be zero")
        expected_children = {n["route_id"] for n in nodes if n["parent"] == node["route_id"]}
        if set(node["children"]) != expected_children:
            raise ValueError("invalid children linkage")
        if node["status"] in {"quick_tested", "promoted"} and node["quick_test_score"] is None:
            raise ValueError("tested/promoted nodes need empirical score")
    promoted = [n["route_id"] for n in nodes if n["status"] == "promoted"]
    if promoted != ([tree["promoted_route_id"]] if tree["promoted_route_id"] else []):
        raise ValueError("inconsistent promotion state")


def save_tree(tree: dict[str, Any], path: str | Path) -> Path:
    validate_tree(tree)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def stats(tree: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in tree["nodes"]:
        counts[node["status"]] = counts.get(node["status"], 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded route tree. Scores are supplied empirical evidence; no scientific search is launched.")
    parser.add_argument("--stats", type=Path)
    parser.add_argument("--tree", type=Path)
    parser.add_argument("--init", metavar="PROBLEM_ID")
    parser.add_argument("--action", choices=["add", "review", "quick-test", "revise", "prune", "beam", "promote"])
    parser.add_argument("--payload", type=Path, help="JSON keyword arguments for the action")
    parser.add_argument("--manifest", type=Path, help="existing human G2 record for promote")
    args = parser.parse_args()
    if args.stats:
        tree = load_tree(args.stats)
    else:
        if not args.tree:
            parser.error("--tree is required unless --stats is used")
        if args.init and args.tree.exists():
            parser.error("refusing to overwrite an existing tree")
        tree = new_tree(args.init) if args.init else load_tree(args.tree)
        if args.action:
            if not args.payload:
                parser.error("--action requires --payload")
            payload = json.loads(args.payload.read_text(encoding="utf-8"))
            handlers = {"add": add_route, "review": record_review, "quick-test": record_quick_test,
                        "revise": revise, "prune": prune, "beam": prune_below_beam, "promote": promote}
            if args.action == "promote":
                payload["manifest"] = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
            handlers[args.action](tree, **payload)
        save_tree(tree, args.tree)
    print(json.dumps({"problem": tree["problem_id"], "used": tree["used"], "status": stats(tree),
                      "promoted": tree["promoted_route_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
