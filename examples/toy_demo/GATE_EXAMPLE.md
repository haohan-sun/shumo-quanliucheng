# Human Gate example (toy demo)

This file shows the Gate mechanics without recording anything.  It is a worked
example, **not** an approval record: no command in this repository can approve a
Gate, and the demo deliberately leaves every Gate pending.

## The seven Gates

| Gate | Decision the human makes | Artifacts the decision binds |
| --- | --- | --- |
| G1 | which problem to solve | selected problem statement |
| G2 | which modelling route to pursue | route tree id, problem id, tree hash |
| G3 | freeze the model specification | `MODEL_SPEC.md` |
| G4 | accept the baseline | baseline run id and metrics |
| G5 | freeze the final method and results | results registry and run ids |
| G6 | approve the formal figures | figure manifest |
| G7 | allow submission | the whole submission set |

## How a real approval is recorded

Only an explicit human instruction is accepted.  The record is written by the
gate CLI, which refuses AI approvers and refuses to run out of order:

```powershell
.\.venv\Scripts\python.exe 90_工具与配置\scripts\gate_control.py approve G1 `
  --approved-by "team-lead" `
  --note "chosen because the data supports it" `
  --selected-problem "toy decay problem"
```

After a human decision, the approval is bound to the current artifacts.  If a
bound artifact later changes, the Gate and every downstream Gate become invalid
automatically — see `03_建模工作区/decisions/DECISION_LOG.md` and the
`artifact_state` snapshots.

## In this demo

* G1..G7 remain `pending` in `run-manifest.json`.  The demo never edits it.
* The demo's run, figure and claim are *evidence*, not approval.  That is why the
  figure's `verification_status` is `unverified`.
* `run_demo.py` prints `Gate status: untouched` as its last line so a reader can
  see the boundary in the output itself.

## What agents may and may not do

Agents, Skills, tests and hooks may report readiness, produce evidence, and tell
you a Gate is ready.  They may not pass it.  If a stage is blocked on a Gate, the
correct output is the blocker and the evidence, never an inferred approval.
