# Methodology sources

This skill was synthesized for this repository. No third-party Skill text or code is copied.
The following public sources informed its separations of responsibility and verification checks.

## Open-source Agent Skills

- [MathModeling-skills](https://github.com/zhnnky329/MathModeling-skills) — MIT. Its separate
  `symbol-table-builder`, `model-assumptions-builder`, and `final-method-explainer` Skills support
  keeping notation, assumptions, and final explanations as distinct auditable artifacts.
- [Math.Skill](https://github.com/Wholiver/Math.Skill) — MIT. Its verification taxonomy motivates
  independent checks such as back-substitution, domain/boundary analysis, dimensional analysis,
  numerical sampling, and limiting cases.
- [verified-computation](https://github.com/heat-death/verified-computation) — MIT. It motivates the
  division in which the agent frames and interprets a derivation while deterministic tools perform
  exact algebra or numerical verification.

## Deterministic modeling tools

- [SymPy documentation](https://docs.sympy.org/) and
  [source repository](https://github.com/sympy/sympy) — symbolic simplification, equation solving,
  calculus and unit-aware checks. Verify identities under stated assumptions; a successful
  simplification is not evidence that the model assumptions match reality.
- [Pyomo documentation](https://pyomo.readthedocs.io/) and
  [source repository](https://github.com/Pyomo/pyomo) — BSD-3-Clause; explicit sets, parameters, variables,
  objectives, constraints and expression components for structured optimization formulations.
- [ModelingToolkit.jl validation documentation](https://docs.sciml.ai/ModelingToolkit/stable/basics/Validation/)
  and [source repository](https://github.com/SciML/ModelingToolkit.jl) — MIT; equations,
  unknowns and parameters are explicit inspectable objects, and unit validation checks consistency
  rather than silently converting incompatible units.
- [OpenMDAO Dymos optimal-control documentation](https://openmdao.org/dymos/docs/latest/getting_started/optimal_control.html)
  and [source repository](https://github.com/openmdao/dymos) — Apache-2.0; motivates separating
  states, controls, design parameters, dynamics, bounds, path constraints, boundary constraints and
  objectives before choosing a transcription or solver.

## Adaptation rule

Use these sources as design evidence, not as authority for a contest-specific model. The official
problem statement, verified data, selected route and recorded assumptions remain the governing
sources. Check each upstream repository's current license before reusing any code or substantial
text; links and licenses here reflect the review performed on 2026-09-16 for this template.
