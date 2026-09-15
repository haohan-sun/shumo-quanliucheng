---
name: mm-mathematical-derivation
description: "AUTO TRIGGER: after a modeling route is selected and before MODEL_SPEC freeze, when assumptions and problem facts must be turned into auditable equations, objectives, constraints, likelihoods, state transitions, or boundary conditions. DO NOT TRIGGER: route selection, solver choice, implementation, numeric tuning, or paper-only formula formatting. OUTPUT: MODEL_DERIVATION.md with symbol/unit discipline, numbered derivation steps, validity conditions, and independent checks."
---

# Mathematical Model Derivation

Translate one selected modeling route into a concise, verification-ready mathematical derivation.
Write the public derivation and its checks, not a transcript of private reasoning.

## Inputs and boundary

Use the problem analysis, evidence passport, data-audit contract, selected route, and recorded
assumptions. Preserve user-established notation when it is unambiguous. Never choose the final
route, invent missing laws or parameter values, silently strengthen assumptions, or treat a
symbolic simplification as empirical validation.

The canonical output is `03_建模工作区/model/MODEL_DERIVATION.md`. `mm-model-spec` consumes
this artifact; implementation and solver work remain downstream.

## Derivation workflow

1. State the modeled scope, requested outputs, spatial/temporal scale, and what is deliberately
   outside the model.
2. Build one symbol table covering sets, indices, variables, parameters, functions, domains,
   units, and provenance. Resolve collisions before writing equations.
3. Separate problem facts, definitions, modeling assumptions, empirical estimates, and
   mathematical consequences. Every load-bearing assumption must identify where it enters.
4. Choose the governing structure appropriate to the route:
   - mechanistic/dynamic: balances, rates, constitutive relations, initial/boundary conditions;
   - optimization: decisions, feasible set, objective, hard/soft constraints, coupling and scale;
   - probabilistic/statistical: sample space, conditional assumptions, likelihood/loss, priors or
     regularization, estimand and identifiability;
   - network/discrete: nodes, edges, flows, conservation, state transitions and integrality.
5. Derive the formulation in numbered steps. For each non-trivial transformation, cite its basis
   as given fact, definition, assumption, law/theorem, algebraic consequence, or empirical fit,
   and record the conditions under which it is reversible or valid.
6. Present the final formulation as a closed contract: inputs, outputs, objective or governing
   equations, constraints, parameter sources, initial/boundary conditions, and applicable range.
7. Run independent checks before handoff. Use deterministic algebra/numeric tools when available;
   retain exact expressions until approximation is necessary and record the check performed.

## Required checks

- dimensional and unit consistency for every additive equation and objective term;
- domain, sign, range, normalization and denominator checks;
- equation/unknown count, identifiability, feasibility or well-posedness as applicable;
- initial, terminal and boundary condition coverage;
- limiting, degenerate and special-case behavior;
- conservation laws, invariants, monotonicity or symmetry when the model claims them;
- at least one independent check such as back-substitution, symbolic equivalence, finite-difference
  comparison, numerical spot check, or a small exactly solvable instance;
- full coverage of each selected-route requirement, with unresolved gaps explicitly blocking freeze.

## Output contract

`MODEL_DERIVATION.md` must contain:

1. scope and source boundary;
2. canonical symbols, domains and units;
3. assumptions with evidence and impact;
4. numbered derivation with validity conditions;
5. final mathematical formulation;
6. check table with method, result and residual/diagnostic where meaningful;
7. unresolved gaps and a field-by-field handoff to `MODEL_SPEC.md`.

Read [references/methodology-sources.md](references/methodology-sources.md) when provenance for the
workflow or a deterministic verification approach is needed. The reference records concepts and
licenses; do not copy third-party prose or code into the derivation.
