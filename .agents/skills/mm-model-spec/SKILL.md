---
name: mm-model-spec
description: "AUTO TRIGGER: a G2 human-approved route and reviewed MODEL_DERIVATION must be translated into or checked against the authoritative MODEL_SPEC, or a frozen-spec change needs a pending request. DO NOT TRIGGER: G2 route comparison, first-principles derivation, code implementation, optimization, plotting, or direct frozen-spec edits. STAGE: S5-S6 and G3 change control. INPUTS: human-approved decision, MODEL_DERIVATION, evidence, existing spec, and approval metadata. OUTPUTS: MODEL_SPEC draft/check findings or pending MODEL_CHANGE_REQUEST. BOUNDARIES: never freeze without explicit G3 approval or alter frozen mathematics directly."
---

# MM Model Spec

Translate human-approved decisions and `03_建模工作区/model/MODEL_DERIVATION.md` into a precise
model contract. Preserve the derivation's symbols, equations, assumptions, units, validity
conditions and checks; do not create a second mathematical definition silently. Check constraints,
trivial/infeasible cases, traceability and approval metadata. Never mark a model frozen without G3;
for a frozen definition, write a pending change request instead of editing it.
