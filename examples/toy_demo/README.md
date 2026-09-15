# Toy demo: one number, traced end to end

This is the smallest honest example of what the workspace is for.  It is a
**toy** model with synthetic data — no contest problem, no real dataset, no
copyright or privacy exposure — and it exists so a new user can see the whole
chain once, quickly, before starting real work.

Run it:

```powershell
# Windows
.\.venv\Scripts\python.exe 90_工具与配置/scripts/run_demo.py
```

```bash
# Linux / macOS
./.venv/bin/python 90_工具与配置/scripts/run_demo.py
```

Everything the demo produces stays under `examples/toy_demo/build/`.

## The chain it demonstrates

| Step | Workspace concept | Where it lands |
| --- | --- | --- |
| 1 | Problem statement | `PROBLEM.md` |
| 2 | Math derivation (units, assumptions, limiting cases) | `DERIVATION.md` |
| 3 | Frozen model contract | `MODEL_SPEC.md` |
| 4 | Human decisions, including a Gate that is *deliberately* left pending | `GATE_EXAMPLE.md` |
| 5 | Tracked run: git state, input/code hashes, seeds, deps, outputs, metrics | `build/runs/<run_id>/manifest.json` |
| 6 | Figure manifest bound to that run and its hashes | `build/figures/manifest.json` |
| 7 | Claim registry: paper sentence -> run -> hashed artifact | `build/paper/claim_registry.jsonl` |
| 8 | Paper fragment that quotes only registered numbers | `build/paper/fragment.md` |

## What it proves

* A number in the paper fragment is reachable from the run record, whose hashes
  still match the files on disk.
* A claim cannot cite a run that did not execute successfully.
* A Gate that no human approved stays `pending`; nothing in this repository can
  approve it automatically.

## What it does not do

It does not exercise all 22 Skills, does not approve any Gate, does not touch
`03_建模工作区/`, `04_论文与提交/` or `run-manifest.json`, and does not claim to
be independent verification.

Verify a previous demo run without re-running it:

```powershell
.\.venv\Scripts\python.exe 90_工具与配置/scripts/run_demo.py --check-only
```
