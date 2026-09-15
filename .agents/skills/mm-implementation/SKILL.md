---
name: mm-implementation
description: "AUTO TRIGGER: G3 is human-approved and the request is to implement the frozen MODEL_SPEC, create the first baseline, tests, or equation-to-code mapping. DO NOT TRIGGER: pre-G3 code, route/spec changes, post-G4 tuning/ablation/benchmarking, visualization, or read-only audit. STAGE: S7-S8 between G3 and G4. INPUTS: frozen MODEL_SPEC, data contracts, configs, and reproducibility requirements. OUTPUTS: code, tests, baseline artifacts, mapping, and validation. BOUNDARIES: one writer for owned files; never change mathematics or approve G4."
---

# MM Implementation

Implement the approved specification faithfully and minimally. Own only assigned `src/`, `tests/`,
and baseline artifacts. Add deterministic configuration, provenance, and equation mappings. If a
mathematical change is needed, create a pending MODEL_CHANGE_REQUEST and stop that change.
