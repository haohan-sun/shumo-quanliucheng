# Scientific figure workflow

Use this note after the Figure Contract identifies the claim. The visual style guide remains the
normative source for palette, typography and export rules.

## Claim-to-chart matrix

| Scientific intent | Preferred encoding | Required evidence cue | Avoid |
| --- | --- | --- | --- |
| Compare methods across an ordered variable | lines with markers | same x grid, interval or run spread | color-only series |
| Compare estimates among categories | points/intervals or bars with error | error definition and sample size | mean-only bars |
| Show a distribution | ECDF, histogram or violin/box | raw run population or weights | hiding tails in averages |
| Show prediction quality | observed-vs-predicted + identity line | metric and held-out split | fitted data presented as validation |
| Diagnose residuals | residual-vs-fitted + QQ | zero line and residual definition | one aggregate score only |
| Show uncertainty over x | center line + interval band | interval type and level | unlabeled shaded region |
| Show parameter influence | tornado or response curve | baseline and perturbation rule | causal wording from correlation |
| Show multi-objective trade-offs | Pareto scatter/front | objective direction and feasibility | connecting unordered points |
| Show a matrix | annotated sequential/diverging heatmap | scale meaning and colorbar units | rainbow scales |
| Show topology | node-link diagram or adjacency matrix | node/edge meaning and layout seed | decorative force layouts |

## Reproducible production

1. Load only a registered result artifact; retain its run ID and hash.
2. Apply a named style preset before creating the figure.
3. Call a reusable template or a figure-specific function in version-controlled code.
4. Save with `save_figure` to PNG plus PDF/SVG as appropriate.
5. Record source, script, parameters, dimensions, outputs and reviewer status in the manifest.
6. Inspect the raster preview at 100% and at intended publication size.

Synthetic data are acceptable only for template tests and exploratory previews that are explicitly
labelled and kept outside the formal figure directory and manifest.
