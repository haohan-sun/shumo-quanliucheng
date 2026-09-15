# Figure contract: toy demo decay fit

A figure is a scientific claim with a picture attached.  This contract is written
before rendering and is referenced by
`examples/toy_demo/build/figures/manifest.json`.

## Claim

The single-exponential model with an additive offset reproduces the observed
decay to within the residual scale of the synthetic dataset.

## Data provenance

* Source: `examples/toy_demo/build/runs/<run_id>/artifacts/predictions.json`
* Produced by the run recorded in that directory's `manifest.json`.
  The renderer must not read raw data directly, so the plotted values are the
  same bytes the run record hashes.

## Encoding decisions

| channel | encodes | rule |
| --- | --- | --- |
| x position | elapsed time | seconds, linear scale |
| y position | response | volts, linear scale |
| filled markers | measured values | one colour |
| solid line | fitted values | a single distinct colour |
| legend | the two series | text plus the same mark, never colour alone |

Axes are labelled with quantity and unit.  No meaning is encoded twice, and the
two series differ by both shape and colour so the figure survives greyscale
printing.

## Required outputs

* `decay_fit.svg` (vector, mandatory for a formal figure)
* `decay_fit.png` (raster preview, optional)

## Acceptance

1. `k` and `rmse` in the subtitle match the run's `metrics.json` exactly.
2. The rendered SVG's hash matches the hash recorded in the run record.
3. The figure manifest names this contract file and the renderer script, and the
   renderer is listed in the run's `code_hashes`.

## Verification status

`unverified` — a human has not yet signed off on this figure.  The demo does not
claim otherwise.
