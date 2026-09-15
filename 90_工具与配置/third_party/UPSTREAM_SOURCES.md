# Upstream Sources

This file records every third-party project this workspace has looked at, what was
taken from it, and under which license. It exists so that "design inspiration" and
"copied code" can never be confused.

Rule for future reuse: record the repository, branch, commit, retrieval date, a
README and LICENSE review, and the reuse conclusion here **before** any code is
brought in.

## Vendored files (verbatim copies)

| Location | Upstream | Commit | License | Notes |
| --- | --- | --- | --- | --- |
| `90_工具与配置/.agents/skills/context-optimization/` | `muratcankoylan/Agent-Skills-for-Context-Engineering` | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | permissive (see upstream `LICENSE`) | Three upstream files tracked as-is; `agents/openai.yaml` is local invocation metadata written for this workspace. Mirrored under the root `.agents/` discovery entry. |

## Design references (no code copied)

| Upstream | License | What it informed | Where it landed |
| --- | --- | --- | --- |
| `SakanaAI/AI-Scientist-v2` | MIT | Budgeted tree search over candidate routes | `mm-route-tournament`, `scripts/route_tree.py` |
| `SamuelSchmidgall/AgentLaboratory` | MIT | Narrow agent roles and phase hand-off artifacts | `90_工具与配置/.codex/agents/*.toml` |
| `Future-House/paper-qa` | Apache-2.0 | Evidence-first citations: locate the source before asserting | `scripts/claim_registry.py` |
| `XiangJinyu/AFlow` | not verified | Score-driven pruning of the route tree | `mm-route-tournament` |
| `jihe520/MathModelAgent` | **AGPL-3.0** | Role separation and local execution only — **zero code reused**, AGPL is deliberately isolated | none (documentation only) |
| `optuna/optuna`, `facebookresearch/hydra`, `IDSIA/sacred` | MIT | Run-record fields: git state, deps, seeds, resolved config | `scripts/run_record.py` |
| `SALib/SALib` | BSD-3-Clause | Sensitivity-method selection order (screen, then quantify) | `scripts/validation_uq.py` |
| `cvxpy`, `Pyomo`, `OR-Tools`, `HiGHS`, `pymoo` | Apache-2.0 / BSD-3-Clause (per project) | Solver portfolio ordering, exact before heuristic | `scripts/solver_strategy.py` |
| `HypothesisWorks/hypothesis` | Apache-2.0 | Property-style invariant tests for pure functions | `03_建模工作区/tests/` |
| `zhnnky329/MathModeling-skills`, `Wholiver/Math.Skill`, `heat-death/verified-computation` | MIT | Separation of notation, assumptions and verification checks in a derivation | `mm-mathematical-derivation` (see its `references/methodology-sources.md`) |
| SymPy, Pyomo, ModelingToolkit.jl, OpenMDAO Dymos documentation | MIT / BSD-3-Clause / Apache-2.0 | Deterministic verification tools and model-structure separation | `mm-mathematical-derivation` references |
| Various community competition-paper skill collections | mixed, unverified | Checklist items only (figure choice, empty abstracts) | `references/` documents |

## Explicit rejections

- Fully automatic research pipelines without human gates — incompatible with the
  G1–G7 approval model and with competition integrity rules.
- Automatic acceptance based only on an LLM judge — scoring must include
  deterministic validators.
- Heavy infrastructure (vector databases, MongoDB, OmegaConf) — a local, file-based
  implementation is sufficient here.
- Any code from AGPL-licensed projects.
