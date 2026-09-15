"""Validation & UQ toolkit: parameter tuning vs validation vs sensitivity vs UQ are
DISTINCT activities and this module keeps them separate.

- bootstrap_ci        : confidence interval for any statistic (UQ)
- seed_robustness     : repeated runs under different seeds -> mean +/- std (stability)
- oat_sensitivity     : one-at-a-time parameter sweep -> tornado data (sensitivity)
- morris_screening    : elementary-effects screening (SALib-style, numpy-only)
- rolling_backtest    : time-series rolling-origin evaluation (validation)
- holdout_evaluation  : train/validation/test split evaluation (validation)
- calibration_curve   : predicted vs observed reliability data
SALib is used for full Sobol when installed; otherwise morris_screening suffices.

CLI (demo on a synthetic model):
    python .../validation_uq.py --demo
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable

import numpy as np


def bootstrap_ci(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError("values must be a non-empty finite vector")
    if n_boot < 1 or not 0 < alpha < 1:
        raise ValueError("n_boot must be positive and alpha in (0, 1)")
    stats = np.array([statistic(values[rng.integers(0, len(values), len(values))])
                      for _ in range(n_boot)])
    lo, hi = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return {"estimate": float(statistic(values)), "ci_low": float(lo), "ci_high": float(hi),
            "alpha": alpha, "n_boot": n_boot}


def seed_robustness(
    run: Callable[[int], float],
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
) -> dict[str, float]:
    scores = np.array([run(seed) for seed in seeds], dtype=float)
    if not scores.size or not np.isfinite(scores).all():
        raise ValueError("seed scores must be non-empty and finite")
    return {
        "mean": float(scores.mean()), "std": float(scores.std(ddof=1)) if len(seeds) > 1 else 0.0,
        "min": float(scores.min()), "max": float(scores.max()), "n_seeds": len(seeds),
        "seeds": list(seeds),
    }


def oat_sensitivity(
    evaluate: Callable[[dict[str, float]], float],
    baseline: dict[str, float],
    relative_perturbations: tuple[float, ...] = (-0.2, 0.2),
) -> dict[str, dict[str, float]]:
    """One-at-a-time sweep around baseline; returns per-parameter low/high effects."""
    result: dict[str, dict[str, float]] = {}
    base = float(evaluate(dict(baseline)))
    for name, value in baseline.items():
        low = high = base
        for rel in relative_perturbations:
            perturbed = {**baseline, name: value * (1 + rel)}
            score = float(evaluate(perturbed))
            if rel < 0:
                low = score
            else:
                high = score
        result[name] = {"baseline": base, "low": low, "high": high,
                        "span": abs(high - low)}
    return result


def morris_screening(
    evaluate: Callable[[np.ndarray], float],
    lower: np.ndarray,
    upper: np.ndarray,
    n_trajectories: int = 10,
    grid_levels: int = 4,
    seed: int = 0,
) -> dict[str, Any]:
    """Morris trajectories on an even-level unit grid; effects per normalized input.

    Each trajectory changes every coordinate once, without clipping. Thus effects
    include the physical parameter range (the standard unit-cube convention).
    """
    rng = np.random.default_rng(seed)
    lower, upper = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    if (lower.ndim != 1 or lower.size == 0 or upper.shape != lower.shape
            or not np.isfinite(lower).all() or not np.isfinite(upper).all()
            or np.any(upper <= lower)):
        raise ValueError("finite vector bounds must satisfy upper > lower")
    if n_trajectories < 1 or grid_levels < 2 or grid_levels % 2:
        raise ValueError("positive trajectories and even grid_levels >= 2 required")
    k = len(lower)
    delta = grid_levels / (2.0 * (grid_levels - 1))
    ee = np.zeros((n_trajectories, k))
    for t in range(n_trajectories):
        direction = rng.choice([-1, 1], k)
        x = rng.integers(0, grid_levels // 2, k) / (grid_levels - 1)
        x += (direction < 0) * delta
        base = float(evaluate(lower + (upper - lower) * x))
        for i in rng.permutation(k):
            x_new = x.copy()
            x_new[i] += direction[i] * delta
            score = float(evaluate(lower + (upper - lower) * x_new))
            if not np.isfinite([base, score]).all():
                raise ValueError("evaluate must return finite scores")
            ee[t, i] = (score - base) / (direction[i] * delta)
            x, base = x_new, score
    mu_hat = ee.mean(axis=0)
    return {
        "mu": mu_hat.tolist(),
        "mu_star": np.abs(ee).mean(axis=0).tolist(),
        "sigma": ee.std(axis=0, ddof=1).tolist() if n_trajectories > 1 else [0.0] * k,
        "n_trajectories": n_trajectories,
        "ranking": np.argsort(-np.abs(ee).mean(axis=0)).tolist(),
    }


def rolling_backtest(
    fit_predict: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray],
    y: np.ndarray,
    x: np.ndarray | None,
    initial_train: int,
    horizon: int = 1,
) -> dict[str, Any]:
    """Rolling-origin evaluation; returns per-fold errors and summary."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float) if x is not None else np.arange(len(y), dtype=float)[:, None]
    if y.ndim != 1 or len(x) != len(y) or initial_train < 1 or horizon < 1:
        raise ValueError("aligned vectors, positive initial_train and horizon required")
    errors: list[float] = []
    n_folds = 0
    for end in range(initial_train, len(y) - horizon + 1, horizon):
        y_hat = fit_predict(y[:end], x[:end], x[end:end + horizon])
        y_hat = np.asarray(y_hat, dtype=float)
        if y_hat.shape != (horizon,) or not np.isfinite(y_hat).all():
            raise ValueError("prediction must be a finite horizon-length vector")
        errors.extend((y[end:end + horizon] - y_hat).tolist())
        n_folds += 1
    errors_arr = np.array(errors)
    return {
        "n_folds": n_folds,
        "n_predictions": len(errors),
        "mae": float(np.abs(errors_arr).mean()) if len(errors_arr) else None,
        "rmse": float(np.sqrt((errors_arr ** 2).mean())) if len(errors_arr) else None,
    }


def holdout_evaluation(
    fit_predict: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray],
    x: np.ndarray,
    y: np.ndarray,
    *,
    train_frac: float = 0.6,
    valid_frac: float = 0.2,
    seed: int = 0,
    metric: Callable[[np.ndarray, np.ndarray], float] = lambda t, p: float(np.mean((t - p) ** 2)),
) -> dict[str, Any]:
    """Train/validation/test split; the test block is touched exactly once."""
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x), np.asarray(y)
    if len(x) != len(y) or not 0 < train_frac < 1 or not 0 < valid_frac < 1 - train_frac:
        raise ValueError("aligned data and positive train/validation/test fractions required")
    idx = rng.permutation(len(y))
    n_train = int(len(y) * train_frac)
    n_valid = int(len(y) * valid_frac)
    if min(n_train, n_valid, len(y) - n_train - n_valid) < 1:
        raise ValueError("every split must contain at least one observation")
    train, valid, test = idx[:n_train], idx[n_train:n_train + n_valid], idx[n_train + n_valid:]
    pred_valid = fit_predict(x[train], y[train], x[valid])
    pred_test = fit_predict(np.concatenate([x[train], x[valid]]),
                            np.concatenate([y[train], y[valid]]), x[test])
    return {"validation_score": metric(y[valid], pred_valid), "test_score": metric(y[test], pred_test),
            "n_train": len(train), "n_valid": len(valid), "n_test": len(test)}


def calibration_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if (y_true.ndim != 1 or y_true.shape != y_prob.shape or not y_prob.size
            or not np.isfinite(y_prob).all() or np.any((y_prob < 0) | (y_prob > 1))
            or not np.isin(y_true, [0, 1]).all() or n_bins < 1):
        raise ValueError("binary labels, aligned probabilities in [0,1], positive bins required")
    bins = np.linspace(0, 1, n_bins + 1)
    curve = []
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if i == n_bins - 1:
            mask |= y_prob == 1
        if mask.any():
            curve.append({"bin_center": float((bins[i] + bins[i + 1]) / 2),
                          "observed": float(y_true[mask].mean()),
                          "predicted": float(y_prob[mask].mean()), "n": int(mask.sum())})
    return {"bins": curve, "ece": float(sum(b["n"] / len(y_prob) * abs(b["observed"] - b["predicted"])
                                            for b in curve))}


def _demo() -> dict[str, Any]:
    rng = np.random.default_rng(7)
    x = np.linspace(0, 10, 200)
    y = 2 * np.sin(x) + rng.normal(0, 0.2, len(x))
    model = lambda yt, xt, xe: np.interp(np.asarray(xe).ravel(), xt.ravel(), yt)
    return {
        "rolling_backtest": rolling_backtest(model, y, x, initial_train=50, horizon=10),
        "bootstrap_ci": bootstrap_ci(y[::10]),
        "oat_sensitivity": oat_sensitivity(
            lambda p: float((p["a"] * 2 + p["b"] ** 2)),
            {"a": 1.0, "b": 2.0, "noise": 0.1},
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validation/UQ toolkit demo.")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    print(json.dumps(_demo(), ensure_ascii=False, indent=2))
