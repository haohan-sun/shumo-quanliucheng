---
name: mm-scientific-visualization
description: "AUTO TRIGGER: G5 is human-approved and the request is to design/render a figure, plot, chart, Figure Contract, or figure-level traceability QA from real registered results. DO NOT TRIGGER: result scientific-validity audit, data discovery, experiment optimization, decorative imagery, paper-wide audit, or final figure approval. STAGE: S11 between G5 and G6. INPUTS: scientific claim, result IDs, real data, style guide, and manifest. OUTPUTS: reproducible rendering code, PNG/vector files, contract, and manifest update. BOUNDARIES: own figures only; never fabricate data or approve G6."
---

# MM Scientific Visualization

Create a Figure Contract before plotting. Bind every formal figure to real data/result sources,
rendering code, and a manifest record. Own only assigned `figures/` artifacts. Follow the style
guide and produce PNG plus vector output where appropriate; stop for human G6 approval.

## Workflow

1. State one scientific question and the claim the figure must support.
2. Resolve the registered result, run ID, variables, units, uncertainty and data grain.
3. Complete `90_工具与配置/templates/FIGURE_CONTRACT_TEMPLATE.md` before rendering.
4. Select an encoding from `references/scientific-figure-workflow.md`; prefer the simplest form
   that exposes comparison, distribution, relationship, uncertainty or mechanism.
5. Render through `src/viz/style_presets.py` and `src/viz/templates.py`. Add a new reusable
   template only when no existing template preserves the intended semantics.
6. Export a 300 dpi PNG preview and PDF/SVG vector output where the chart type permits it.
7. Run numeric, semantic, visual and traceability QA; inspect the actual rendered image.
8. Register the contract, script, source result/run and output files in the figure manifest.

The exact palette and semantic encoding rules live only in
`90_工具与配置/configs/VISUAL_STYLE_GUIDE.md`; do not duplicate them in public-facing overview
documents.

## Template selection

- Trend or method comparison: `line_comparison`.
- Estimate comparison with sampling uncertainty: `bar_with_error`.
- Dense matrix: `heatmap_annotated`.
- Regression adequacy: `residual_diagnostic` and `observed_vs_predicted`.
- Parameter influence: `sensitivity_tornado`.
- Multi-objective trade-off: `pareto_front`.
- Topology or flow relation: `network_graph`.
- Interval or scenario uncertainty: `uncertainty_band`.
- Distribution or stochastic runs: `distribution_ecdf`.

Do not use a template merely because it is available. The Figure Contract must explain why its
encoding answers the stated scientific question.

## Required QA

- Data are finite where required and lengths/shapes agree.
- Axis labels, units, transformations, aggregation and uncertainty definitions are explicit.
- Categorical series have redundant marker/line/hatch encodings where color alone may fail.
- Sequential, diverging and cyclic variables use semantically appropriate color mappings.
- The figure remains interpretable in grayscale and at final single-column size.
- Reference lines (zero, identity, chance or target) are included when they define correctness.
- Every visible number is traceable to the registered result bytes and rendering code.
- PNG and vector exports open successfully and have been visually inspected.
