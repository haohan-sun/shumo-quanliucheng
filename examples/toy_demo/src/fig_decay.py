"""Toy demo figure: re-render observations plus the fitted curve.

This script is the standalone renderer.  The baseline script writes the same
figure inside its tracked run, so the renderer is not on the critical path; it
exists so a reader can re-render the figure from a registered
``predictions.json`` without re-running the fit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _toyplot import read_predictions, write_png_if_available, write_svg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Run directory. When set, outputs default to <run-dir>/figures/<name>.",
    )
    parser.add_argument("--svg-out", type=Path)
    parser.add_argument("--png-out", type=Path)
    parser.add_argument("--title", default="Toy demo: exponential decay with offset")
    parser.add_argument("--subtitle", default="")
    args = parser.parse_args()

    svg_out = args.svg_out
    png_out = args.png_out
    if args.run_dir is not None:
        svg_out = svg_out or args.run_dir / "figures" / "decay_fit.svg"
        png_out = png_out or args.run_dir / "figures" / "decay_fit.png"
    if svg_out is None:
        parser.error("provide --svg-out or --run-dir")

    rows = read_predictions(args.predictions)
    write_svg(rows, svg_out, title=args.title, subtitle=args.subtitle)
    wrote_png = False
    if png_out is not None:
        wrote_png = write_png_if_available(
            rows, png_out, title=args.title, subtitle=args.subtitle
        )
    print(f"wrote {svg_out.as_posix()}")
    print(f"png: {'written' if wrote_png else 'skipped (matplotlib unavailable)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
