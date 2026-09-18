# Real-problem regression log

A manual record of running this workspace against real historical competition
problems. The point is to find friction in the *workflow*, not to score the
workspace. Copy the template once per problem and fill it in by hand.

This is deliberately not a framework: there is no runner, no scoring, no
leaderboard, and nothing here is read by the tooling.

## Where the pieces already live

Do not duplicate what the workspace already records:

| What you want to note | Existing home |
| --- | --- |
| the problem itself, attachments, rules | `01_题目与要求/` |
| decisions you made and why | `03_建模工作区/decisions/DECISION_LOG.md` |
| Gate approvals and their bound artifacts | `run-manifest.json` + `90_工具与配置/state/artifact_snapshots.json` |
| formal runs, hashes, metrics, runtime | `03_建模工作区/runs/<run_id>/` and `experiments/registry.csv` |
| claims and the runs behind them | `04_论文与提交/paper/claim_registry.jsonl` |
| bugs and their lessons | `90_工具与配置/state/error_registry.jsonl` (`record_error`) |
| what this log adds | the *cross-cutting* experience: where the workflow itself fought you |

## Template

```markdown
## <problem_id>

- problem_id:
- problem_type:            # optimization / prediction / evaluation / simulation / ...
- mode:                    # research | competition  (from `run.ps1 modes`)
- commit:                  # workspace commit used for this run

### route / decomposition issues
# Did `run.ps1 plan` split the request correctly? Which clause was misrouted or
# fell through to fallback_orchestrator? Did a writer-scope conflict appear?

### gate friction
# Which Gate was awkward? Was an artifact dependency unreasonable? Did a
# `confirm`-tier Gate in competition mode feel right, or did it hide a real check?

### runtime issues
# Setup, environment, solver availability, memory, wall-clock surprises.

### provenance issues
# Anything the tracked run could not hash or bind. Missing git state, paths that
# escaped the workspace, claims that could not be attached to a successful run.

### paper / claim issues
# Numbers you wanted to quote that had no registered run. Figure contracts that
# were painful. Anything that tempted you to type a number by hand.

### bugs found
# Concrete defects, with the command that reproduced them.

### fix commit
# The commit that fixed it, or "not fixed" with the reason.
```

## What to do with the results

- A workflow defect that reproduces across problems is worth fixing.
- A one-off inconvenience is worth writing down and ignoring.
- Anything that makes a Gate easier to pass, or lets a number reach the paper
  without a run, is a bug in the workspace, not a missing feature.
