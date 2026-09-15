# Toy problem statement

A sensor records a quantity that decays over time.  The instrument has a fixed
additive offset that cannot be calibrated out at measurement time.

**Given** `data/decay_observations.csv` with columns

| column | meaning | unit |
| --- | --- | --- |
| `t` | elapsed time | s |
| `y` | measured response | V |

**Estimate** the decay rate `k` and the offset `c` in

    y(t) = a * exp(-k * t) + c

**Deliverable** a point estimate and the root-mean-square error of the fit, on
the observed time grid.

**Constraints**

* The offset `c` is a nuisance parameter: it must be reported, but the scientific
  answer is `k`.
* The response is positive and decays; `a > 0`, `k > 0`.
* No instrument specification is available, so the uncertainty statement is
  limited to the residual scale of this dataset.

This is a synthetic teaching example, not a contest problem.
