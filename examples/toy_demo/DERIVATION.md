# Derivation: exponential decay with an unknown offset

## 1. Symbol table

| symbol | meaning | unit | domain |
| --- | --- | --- | --- |
| `t` | elapsed time | s | `t >= 0` |
| `y` | measured response | V | `y > 0` |
| `a` | amplitude at `t = 0` | V | `a > 0` |
| `k` | decay rate | 1/s | `k > 0` |
| `c` | additive instrument offset | V | unscaled |

Dimensional check: `a * exp(-k * t)` is `V * 1 = V`, and `k * t` is
`(1/s) * s = 1`, so the exponent is dimensionless.  Adding `c` (V) is therefore
consistent.

## 2. Assumptions

| id | assumption | basis | strength |
| --- | --- | --- | --- |
| A1 | The decay is a single exponential. | Problem statement describes one decay. | moderate |
| A2 | Noise is additive, zero-mean and homoscedastic. | No instrument specification; the residual scale is used instead of a stated uncertainty. | weak |
| A3 | The offset `c` is constant over the observation window. | Problem states the offset is fixed. | strong |
| A4 | Sampling times are exact. | No timing error is supplied. | moderate |

A2 is weak, so the reported uncertainty must come from the residuals, not from an
assumed noise model.

## 3. Objective

Least squares on the observed grid:

    minimise  S(a, k, c) = sum_i [ y_i - (a * exp(-k * t_i) + c) ]^2
    subject to  a > 0, k > 0

The reported metric is

    rmse = sqrt( (1/N) * sum_i [ y_i - (a * exp(-k * t_i) + c) ]^2 )   [V]

## 4. Limiting cases (checked before trusting any fit)

* `k -> 0`: the model degenerates to a constant `a + c`; a small fitted `k` is
  therefore not identifiable from a short window.
* `t -> 0`: `y(0) = a + c`, so `a` and `c` trade off at early times.  This is
  the identifiability risk for this model and the reason `c` is reported as a
  nuisance parameter.
* `c = 0`: recovers the textbook single-exponential fit.

## 5. Solver choice

`S` is nonlinear in `k` but linear in `(a, c)` for fixed `k`.  A dense one
dimensional grid over `k` with a closed-form linear solve for `(a, c)` is exact
enough for a toy baseline, deterministic, and needs no derivative information.
A gradient method is left as a later refinement.
