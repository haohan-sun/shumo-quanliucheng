"""Toy demo baseline: fit ``y = a * exp(-k * t) + c`` by grid search.

This script is deliberately small and deterministic.  It is the "implemented
baseline" step of the demo chain and is executed *through*
``scripts/tracked_run.py`` so that its inputs, code, seeds and outputs are
hashed into a run record.

It writes metrics, per-point predictions and the figure in one pass, which is
why a single run can be the provenance root for the whole demo.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toyplot import write_png_if_available, write_svg


def read_observations(path: Path) -> tuple[list[float], list[float]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or {"t", "y"} - set(reader.fieldnames):
            raise ValueError(f"{path.as_posix()} must have 't' and 'y' columns")
        rows = [(float(row["t"]), float(row["y"])) for row in reader]
    if len(rows) < 3:
        raise ValueError("need at least three observations")
    return [t for t, _ in rows], [y for _, y in rows]


def linear_fit_for_k(times: list[float], values: list[float], k: float) -> tuple[float, float, float]:
    """Closed-form least squares for (a, c) at a fixed k; returns (a, c, sse)."""
    basis = [math.exp(-k * t) for t in times]
    n = len(times)
    sum_b = sum(basis)
    sum_bb = sum(b * b for b in basis)
    sum_y = sum(values)
    sum_by = sum(b * y for b, y in zip(basis, values, strict=True))
    denominator = n * sum_bb - sum_b * sum_b
    if abs(denominator) < 1e-12:
        return 0.0, sum_y / n, float("inf")
    a = (n * sum_by - sum_b * sum_y) / denominator
    c = (sum_y - a * sum_b) / n
    sse = sum((y - (a * b + c)) ** 2 for b, y in zip(basis, values, strict=True))
    return a, c, sse


def grid_search(
    times: list[float],
    values: list[float],
    k_min: float,
    k_max: float,
    k_points: int,
) -> dict[str, float]:
    best: dict[str, float] | None = None
    for index in range(k_points):
        k = k_min + (k_max - k_min) * index / (k_points - 1)
        a, c, sse = linear_fit_for_k(times, values, k)
        if a <= 0:
            continue
        if best is None or sse < best["sse"]:
            best = {"a": a, "k": k, "c": c, "sse": sse}
    if best is None:
        raise RuntimeError("no admissible (a > 0) fit found; widen the k grid")
    best["rmse"] = math.sqrt(best["sse"] / len(times))
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--k-min", type=float, default=0.01)
    parser.add_argument("--k-max", type=float, default=2.0)
    parser.add_argument("--k-points", type=int, default=400)
    parser.add_argument("--metrics-out", type=Path, required=True)
    parser.add_argument("--predictions-out", type=Path, required=True)
    parser.add_argument("--svg-out", type=Path, help="Write the figure inside this run.")
    parser.add_argument("--png-out", type=Path, help="Optional raster preview.")
    args = parser.parse_args()

    times, values = read_observations(args.input)
    fit = grid_search(times, values, args.k_min, args.k_max, args.k_points)

    metrics = {
        "a": round(fit["a"], 6),
        "k": round(fit["k"], 6),
        "c": round(fit["c"], 6),
        "rmse": round(fit["rmse"], 6),
        "n_observations": len(times),
        "k_min": args.k_min,
        "k_max": args.k_max,
        "k_points": args.k_points,
    }
    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    args.predictions_out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[float, float, float]] = []
    with args.predictions_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", "y", "y_hat", "residual"])
        for t, y in zip(times, values, strict=True):
            y_hat = fit["a"] * math.exp(-fit["k"] * t) + fit["c"]
            rows.append((t, y, y_hat))
            writer.writerow([f"{t:.3f}", f"{y:.6f}", f"{y_hat:.6f}", f"{y - y_hat:.6f}"])

    if args.svg_out is not None:
        write_svg(
            rows,
            args.svg_out,
            title="Toy demo: exponential decay with offset",
            subtitle=f"fitted k = {metrics['k']} 1/s, rmse = {metrics['rmse']} V",
        )
        print(f"wrote {args.svg_out.as_posix()}")
    if args.png_out is not None:
        wrote = write_png_if_available(
            rows,
            args.png_out,
            title="Toy demo: exponential decay with offset",
            subtitle=f"fitted k = {metrics['k']} 1/s, rmse = {metrics['rmse']} V",
        )
        print(f"png: {'written' if wrote else 'skipped (matplotlib unavailable)'}")

    print(f"fitted a={metrics['a']} k={metrics['k']} c={metrics['c']}")
    print(f"rmse={metrics['rmse']} over n={metrics['n_observations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
