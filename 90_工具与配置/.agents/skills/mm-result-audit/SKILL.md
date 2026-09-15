---
name: mm-result-audit
description: "AUTO TRIGGER: a request questions result consistency, bugs, constraints, validity, provenance, stale dependencies, or reproducibility after baseline/experiments exist. DO NOT TRIGGER: generating/fixing code, tuning, rendering figures, citation-only checks, paper wording, or submission formatting. STAGE: S10 and regression checks before/after G5. INPUTS: MODEL_SPEC, hashes, experiment/results registries, configs, and artifacts. OUTPUTS: read-only findings, reproduction evidence, and stale dependency report. BOUNDARIES: reviewer/critic only; never rewrite a truth source to pass."
---

# MM Result Audit

Compare selected outputs against the model, registries, hashes, configurations, and artifacts.
Reproduce checks where authorized. Report concrete failures and stale dependencies; never alter a
truth source or silently dispatch a writer to make an audit pass.
