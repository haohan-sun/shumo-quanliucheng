# Scientific Visualization Style Guide

This guide applies to future formal figures. Bootstrap creates no result figure.
This is the ONLY authoritative visual policy. `画图SKILL.md` is a legacy reference;
`src/viz/README.md`, `CODE_STYLE.md`, and style presets explain implementation, not competing policy.

1. Write and approve a Figure Contract before plotting.
2. Start from the scientific claim, not a preferred chart type.
3. Match visual encoding to the scientific question and data semantics.
4. Use colorblind-aware palettes and verify grayscale legibility where relevant.
5. Keep typography, notation, units, and sizing consistent across figures.
6. Export vector PDF/SVG where possible.
7. Export a PNG preview for review and manifests.
8. Do not use meaningless 3D.
9. Do not use a rainbow colormap without a documented scientific reason.
10. Do not use decorative gradients.
11. Do not manipulate axes in a misleading way; disclose truncation and transformations.
12. Visualize uncertainty whenever it is relevant to the claim.
13. When distribution matters, do not reduce it to a mean-only bar plot.
14. Sankey, radar, dual-axis, and 3D plots require explicit written justification.
15. Aesthetics may be innovative, but novelty must never reduce scientific interpretability.

## Canonical palette

All newly produced project figures use the following cool purple-blue palette by default:

| Role | Hex |
| --- | --- |
| deep purple-blue / primary | `#4F587D` |
| mid purple / secondary | `#776B97` |
| light purple / highlight | `#C68DC0` |
| ice blue / comparison | `#C2E0EE` |
| light lavender / interval | `#DBC4ED` |

Neutral ink and structure colors are `#1B1F23`, `#4E565E`, `#8C949C`, `#C4CAD1`, and
`#E8EEF4`. The canonical sequential mapping is white → ice blue → light lavender → light
purple → mid purple → deep purple-blue. Do not introduce a new accent color merely to separate
categories: first use marker, line style, hatch, annotation, faceting or direct labels. If more than
five unrelated categories remain essential, document the accessibility reason in the Figure
Contract before selecting an additional colorblind-safe palette.

## Semantic encoding

- Categorical series must not rely on color alone; add markers, line styles, hatches or direct labels.
- Ordered non-negative magnitude uses the canonical sequential mapping. A meaningful midpoint uses
  a perceptually balanced diverging map centered on that reference. Cyclic quantities use a cyclic
  map only when the endpoints are identical in meaning.
- Uncertainty bands state whether they are confidence, credible, prediction, quantile or scenario
  intervals and state the level or construction rule.
- Stochastic algorithms show the run population, interval or distribution; one selected run is not
  evidence of stability.
- Spatial figures state coordinate system, projection, scale and orientation when relevant.
- Dense networks prefer matrices, aggregation or small multiples when a node-link view becomes
  unreadable.
- Calibration, ROC and prediction figures include the appropriate identity, chance or target
  reference and identify the evaluated split.

## Required QA before registration

1. Numeric: inputs have expected shapes, finite values and explicit missing-value handling.
2. Semantic: axes, units, transformations, aggregations and uncertainty definitions are correct.
3. Accessibility: redundant encodings work in grayscale and the intended final size is readable.
4. Integrity: limits, truncation, log scales and smoothing cannot mislead and are disclosed.
5. Export: a 300 dpi PNG and appropriate PDF/SVG open successfully without clipping.
6. Traceability: result bytes, run ID, script, contract and manifest entry agree.
7. Visual inspection: a human or independent reviewer has viewed the actual rendered output.

Every formal figure must bind to real data or a registered result artifact, a reproducible script, a Figure Contract, and `03_建模工作区/figures/manifest.json`. Never use LLM-invented data as a formal result.

## Implementation contract

- Use `src/viz/style_presets.py` (`apply_style`, `save_figure`) for consistent defaults;
  justified semantic encodings may override individual artist properties, not silently replace policy.
- Label relevant axes with meaning and units; provide legends where needed. Export PNG previews
  at 300 dpi and vector PDF/SVG when appropriate. File names must identify the figure and claim.
- Formal figures use registered results and run IDs. Pre-G5 exploratory synthetic previews stay
  in `experiments/scratch/`, are explicitly labelled, and cannot enter the formal figure manifest.
- An altered data source, rendering code, or contract invalidates prior figure acceptance;
  only a human may approve G6 again. A template rendering test is not figure approval.
