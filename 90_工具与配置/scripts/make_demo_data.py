"""Generate the toy demo dataset (deterministic, synthetic, no real data).

Usage:
    python 90_工具与配置/scripts/make_demo_data.py [--out examples/toy_demo/data/decay_observations.csv]

The series is a single exponential with an additive offset plus a small fixed
noise sequence.  The noise is generated from a seeded linear congruential
generator so the file is byte-identical on every platform and every run -- a
reproducibility fixture must not depend on a library's RNG implementation.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT

AMPLITUDE = 2.5
DECAY_RATE = 0.35
OFFSET = 0.4
POINTS = 24
STEP = 1.0
NOISE = 0.02
SEED = 20260905

DEFAULT_OUT = ROOT / "examples" / "toy_demo" / "data" / "decay_observations.csv"


def noise_sequence(count: int, seed: int = SEED, amplitude: float = NOISE) -> list[float]:
    """Deterministic noise in [-amplitude, amplitude] from a 32-bit LCG."""
    state = seed & 0xFFFFFFFF
    values: list[float] = []
    for _ in range(count):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        unit = state / 0x7FFFFFFF  # [0, 1]
        values.append((unit - 0.5) * 2.0 * amplitude)
    return values


def series(points: int = POINTS, step: float = STEP) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for index, offset in enumerate(noise_sequence(points)):
        t = index * step
        y = AMPLITUDE * math.exp(-DECAY_RATE * t) + OFFSET + offset
        rows.append((t, y))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--points", type=int, default=POINTS)
    args = parser.parse_args()

    rows = series(points=args.points)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["t,y"]
    lines.extend(f"{t:.3f},{y:.6f}" for t, y in rows)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out.as_posix()} ({len(rows)} rows)")
    print(f"true parameters: a={AMPLITUDE}, k={DECAY_RATE}, c={OFFSET}, noise=+/-{NOISE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
