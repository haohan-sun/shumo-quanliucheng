# MODEL_SPEC (toy demo)

Status: `FROZEN`
Version: `toy-1.0`

This is the authoritative model contract for the toy demo.  It is frozen so that
the run record can carry a stable `model_spec_version`; nothing downstream may
change the mathematics without a human-recorded decision.

## Model

For observation `i` at time `t_i`:

    y_hat_i = a * exp(-k * t_i) + c
    residual_i = y_i - y_hat_i

Parameters: `a > 0` (V), `k > 0` (1/s), `c` (V, nuisance).

## Estimator

Grid search over `k` on `[k_min, k_max]` with `k_points` samples.  For each `k`,
solve the linear least-squares problem for `(a, c)` in closed form, then keep the
`k` with the smallest `S`.  Report `a`, `k`, `c`, `rmse`, and the number of
observations.

## Inputs

* `examples/toy_demo/data/decay_observations.csv` (`t`, `y`)
* `k_min = 0.01`, `k_max = 2.0`, `k_points = 400`

## Outputs

* `metrics.json` — point estimates and `rmse`
* `predictions.csv` — `t`, `y`, `y_hat`, `residual`
* `figure.svg` — observations and fitted curve

## Acceptance criteria

1. `rmse` is below `0.05` V on the shipped synthetic dataset.
2. The fitted curve is drawn only from a run whose record validates.
3. The `rmse` quoted in the paper fragment equals the value in the run record.

## Change control

Any change to the estimator, the acceptance threshold, or the reported metric is
a spec change: record a `MODEL_CHANGE_REQUEST` and obtain a human decision
before implementation.  Agents may report readiness; they may not freeze a spec.
