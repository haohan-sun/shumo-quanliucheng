---
name: mm-preflight
description: "AUTO TRIGGER: mm-orchestrator detects a new/stale stage, missing state, readiness request, environment check, or input inventory. DO NOT TRIGGER: substantive literature research, model design, implementation, experiments, or generic status already available. STAGE: SessionStart and S0/phase entry. INPUTS: manifest, layout, official inputs, contracts, tools, and hashes. OUTPUTS: readiness BLOCKER/WARNING/INFO and stale-state report. BOUNDARIES: inspect readiness only; never solve the problem, select a method, or approve a Gate."
---

# MM Preflight

Inspect only readiness: problem files, data presence, tool availability, contracts, manifests, and
stage prerequisites. Return evidence-backed missing, optional, blocking, and stale items to the
orchestrator. Do not infer a model, generate results, or modify truth sources.
