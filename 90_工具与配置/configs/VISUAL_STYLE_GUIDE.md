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
