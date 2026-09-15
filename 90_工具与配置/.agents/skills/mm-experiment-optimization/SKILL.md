---
name: mm-experiment-optimization
description: "AUTO TRIGGER: G4 baseline is human-approved and the request is parameter tuning, solver comparison, ablation, performance benchmark, or search aimed at improving the approved baseline. DO NOT TRIGGER: validation, sensitivity, robustness, calibration, or uncertainty claims (mm-validation-uq); initial implementation; route changes; figure design; result audit. STAGE: S9 between G4 and G5. INPUTS: approved baseline, experiment contract, metrics, seeds, and budget. OUTPUTS: registered tuning/comparison experiments and negative results. BOUNDARIES: own experiment/result artifacts; never reuse tuning evidence as validation, redefine mathematics, or approve G5."
---

# MM Experiment Optimization

Operate only on a G4-approved implementation. Register inputs, config, parameters, seed, metrics,
constraint violation, runtime, status, and artifacts. Preserve negative results. Do not edit files
owned by another writer; route any mathematical change through a pending change request.
