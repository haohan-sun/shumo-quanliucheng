---
name: mm-orchestrator
description: "AUTO TRIGGER: every non-trivial project request, including ambiguous requests to continue. DO NOT TRIGGER: casual chat, literal navigation, or one-line file lookup. STAGE: S0-S15 and G1-G7. INPUTS: natural-language request, AGENTS.md, run-manifest, decision log, and artifact state. OUTPUTS: one task classification, stage, selected functional mm-* Skill, subagent plan, dependencies, Gate stop, validation, and synthesis. BOUNDARIES: route and coordinate only; never perform all specialist work, select the final model, or approve a Human Gate."
---

# MM Orchestrator

1. Read `AGENTS.md`, `run-manifest.json`, the decision log, and project status before routing.
2. Classify the request with `90_工具与配置/configs/auto-routing.yaml`; choose one primary
   functional Skill and add review/provenance sidecars only when needed.
3. Check stage prerequisites and stop at G1-G7 until an explicit human approval is recorded.
4. Delegate independent work to narrow subagents. Run read-only work in parallel when useful;
   assign one writer per artifact and serialize writer/reviewer handoffs.
5. Run relevant validation and record material AI use. Do not expose hidden reasoning or turn the
   submission report into a dispatch trace.
6. Synthesize specialist outputs without inventing evidence, completion, or approval.

## Executable routing and handoffs

For a request that contains more than one job, do not route it as a single task.
Run the decomposition handoff first:

```
python 90_工具与配置/scripts/decompose.py "<request>" --json
```

* `decomposed: false` - the request is atomic; continue with `auto_route.py`
  exactly as before. This is the path for every simple request, so the common
  case stays unchanged.
* `decomposed: true` - dispatch the reported tasks. Each task carries the router
  decision produced by the unchanged `route_task()`; do not pick a Skill
  yourself, and do not merge two tasks into one writer.
* Honour `execution_waves`: tasks in the same wave may run concurrently only when
  their `writer_scope` differ. Read-only reviewers may always run concurrently.
* `gate_stops` are Human Gate boundaries. Stop and report; never approve, skip,
  or reorder a Gate to keep the plan moving.
* `blocked_prerequisite` lists tasks waiting on an unapproved Gate. Report them
  as blockers.
* `errors` (for example a writer-scope conflict) must be reported to the human
  with the conflicting task ids, and the artifact owner decided explicitly.

Decomposition is a planning step only: it writes no manifest, records no
approval, and adds no provenance entry of its own.


Use `python 90_工具与配置/scripts/auto_route.py "<request>"` to obtain the routing
decision. This command previews dispatch; it does not spawn agents or run experiments.
Only `action=route` authorizes its listed execution plan. Pending or artifact-invalidated
prerequisite Gates stop all writers. The router checks artifact snapshots on every
substantive dispatch without writing a new approval or changing the caller's manifest.

Execute `preflight_skills` first when their required artifacts are missing, invalid,
or stale; a file's existence is not readiness. Then execute `preprocessors`, the
`primary_skill` using the declared `inputs`/`entrypoints`, and `postprocessors`.
Use the real validators from the selected skill and persist its declared `outputs`.
Do not report the command preview as a completed specialist run.

The connected sequence is evidence -> mm-problem-analysis (S2b) -> mm-data-audit
(S2c) -> bounded mm-route-tournament -> human G2 -> mm-mathematical-derivation ->
MODEL_SPEC -> human G3 ->
mm-solver-strategy (S6b) -> implementation -> human G4 -> optimization and separate
mm-validation-uq (S9b) -> human G5 -> figures/paper. Existing G1-G7 IDs are unchanged.
Validate PROBLEM_ANALYSIS with `scripts.problem_analysis.check_analysis`; blocked
data audits stop route/spec completion. Implementation consumes SOLVER_STRATEGY
and the preprocessing contract rather than merely checking that files exist.

Wrap important computation and figure runs with mm-reproducibility **before execution**
(`create_run`) and after (`finalize_run`); an after-only record is not reproducibility.
Paper writing is a separate primary route. Use mm-cumcm-paper-writing-review only for
CUMCM-specific writing or evidence-based review; the main agent remains the sole prose writer.
reviewer/validator/replicator assess the resulting evidence after handoff. Every numeric
claim must resolve through claim_registry to a verified run and its current output hashes.
The parent owns persistence when a read-only agent returns findings.

Use validator for statistical validity and leakage, replicator for independent hashes
and reproduction, and judge for bounded route adjudication. All three are read-only;
none may approve a Gate. Replication requiring file writes is executed by the parent
in isolated scratch, followed by independent inspection. Judge recommendations stop at G2.
Visual work reads `90_工具与配置/configs/VISUAL_STYLE_GUIDE.md` as the only normative
style source; templates and legacy documents explain implementation only.
