#!/usr/bin/env python3
"""Run the toy demo: one number traced from input to paper claim.

The demo is self-contained and synthetic.  It writes only under
``examples/toy_demo/build/`` and never touches ``03_建模工作区/``,
``04_论文与提交/`` or ``run-manifest.json``.

Pipeline

1. hash the dataset into a tracked run (``scripts/tracked_run.py`` machinery)
2. execute the frozen baseline inside that run
3. render the figure, also inside the run, and register it as a run output
4. write the figure manifest bound to the run and its hashes
5. register the claim, then re-verify run -> artifact -> claim
6. write the paper fragment, quoting only the registered number

Exit codes: 0 success, 1 the demo ran but a check failed, 2 the environment is
not ready.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, dump_json, load_json, resolve_python, sha256_file
from scripts.claim_registry import check_registry
from scripts.run_record import validate_run_record
from scripts.tracked_run import _output_spec, execute_tracked

DEMO = ROOT / "examples" / "toy_demo"
BUILD = DEMO / "build"
RUNS = BUILD / "runs"
DATA = DEMO / "data" / "decay_observations.csv"
CODE = DEMO / "src" / "fit_decay.py"
FIG_CODE = DEMO / "src" / "fig_decay.py"
PLOT_CODE = DEMO / "src" / "_toyplot.py"
SPEC = DEMO / "MODEL_SPEC.md"
CONTRACT = DEMO / "FIGURE_CONTRACT.md"

# The demo's frozen configuration.  It is written verbatim into the run record's
# config/resolved.json, so every number in the paper fragment is reproducible.
CONFIG: dict[str, object] = {
    "model": "toy-decay-with-offset",
    "model_spec_version": "toy-1.0",
    "estimator": "grid-search-k-with-closed-form-linear-fit",
    "k_grid": {"min": 0.01, "max": 2.0, "points": 400},
    "dataset": "examples/toy_demo/data/decay_observations.csv",
}

SETUP_HINT = (
    "the demo needs the project environment; run setup first:\n"
    "  Windows :  .\\setup.ps1\n"
    "  POSIX   :  ./setup.sh"
)


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def check_environment() -> None:
    missing = [path for path in (DATA, CODE, FIG_CODE, SPEC, CONTRACT) if not path.is_file()]
    if missing:
        raise SystemExit(
            "demo inputs are missing:\n  "
            + "\n  ".join(relative(path) for path in missing)
            + "\nRestore them from the repository."
        )


def tracked(*, command: list[str], outputs: list[str], code: list[Path],
            inputs: list[Path], config: dict) -> Path:
    """Execute one tracked run and return the finalized run directory."""
    RUNS.mkdir(parents=True, exist_ok=True)
    exit_code, manifest_path = execute_tracked(
        command,
        config=config,
        seeds={"main": 20260905},
        inputs=[item.resolve() for item in inputs],
        code_paths=[item.resolve() for item in code],
        # `execute_tracked` wants (path, kind) pairs; reuse the project's own
        # "KIND=PATH" parser instead of reimplementing it.
        outputs=[_output_spec(spec, ROOT) for spec in outputs],
        timeout=300,
        cwd=str(ROOT),
        runs_root=RUNS,
        root=ROOT,
    )
    run_dir = manifest_path.parent
    if exit_code:
        manifest = load_json(manifest_path) if manifest_path.is_file() else {}
        raise SystemExit(
            f"tracked step failed with exit code {exit_code}\n"
            f"  run: {relative(run_dir)}\n"
            f"  command: {' '.join(manifest.get('command', []))}\n"
            "  see stderr.log in the run directory"
        )
    return run_dir


def step_data() -> str:
    print(f"[1/6] input dataset: {relative(DATA)}")
    print(f"      sha256: {sha256_file(DATA)}")
    return sha256_file(DATA)


def step_run(config: dict) -> tuple[dict, dict, Path]:
    """One tracked run that produces the metrics, the predictions and the figure.

    Keeping them in a single run is what makes the provenance chain simple: one
    run id roots the numbers, the plotted values and the figure bytes.
    """
    figures = RUNS / "figures"
    # Paths passed to the child are absolute (a tracked run keeps cwd at the
    # project root); absolute paths are still recorded root-relative.
    run_dir = tracked(
        command=[
            # Canonical interpreter path: on POSIX the project interpreter is a
            # venv symlink pointing outside the workspace, which a tracked run
            # would reject as an artifact escaping the project.
            resolve_python(),
            str(CODE),
            "--input",
            str(DATA),
            "--k-min",
            str(config["k_grid"]["min"]),
            "--k-max",
            str(config["k_grid"]["max"]),
            "--k-points",
            str(config["k_grid"]["points"]),
            "--metrics-out",
            str(RUNS / "metrics.json"),
            "--predictions-out",
            str(RUNS / "predictions.json"),
            "--svg-out",
            str(figures / "decay_fit.svg"),
            "--png-out",
            str(figures / "decay_fit.png"),
        ],
        outputs=[
            f"metrics={RUNS / 'metrics.json'}",
            f"artifact={RUNS / 'predictions.json'}",
            f"figure={figures / 'decay_fit.svg'}",
        ],
        code=[CODE, PLOT_CODE],
        inputs=[DATA],
        config=config,
    )
    record = load_json(run_dir / "manifest.json")
    metrics = load_json(run_dir / "artifacts" / "metrics.json")
    print(f"[2/6] tracked run: {record['run_id']}")
    print(f"      code hash : {record['code_hashes'].get(relative(CODE), 'n/a')[:16]}...")
    print(f"      inputs    : {list(record['input_hashes'])}")
    print(f"      metrics   : k={metrics['k']} rmse={metrics['rmse']}")
    print(f"      outputs   : {[entry['path'] for entry in record['outputs']]}")
    return record, metrics, run_dir


def step_figure(record: dict, metrics: dict, run_dir: Path) -> Path:
    """Write the figure manifest bound to the run that produced the figure."""
    run_id = str(record["run_id"])
    predictions = run_dir / "artifacts" / "predictions.json"
    # ``add_output`` preserves a declared path when it is already inside the run
    # directory and otherwise copies it to artifacts/; resolve the real path from
    # the record's own output list so the manifest never points at a stale path.
    registered = {Path(entry["path"]).name: entry for entry in record["outputs"]}
    if "decay_fit.svg" not in registered:
        raise SystemExit("the figure was not registered as a run output")
    svg = run_dir / registered["decay_fit.svg"]["path"]
    png_entry = registered.get("decay_fit.png")
    png = run_dir / png_entry["path"] if png_entry else None
    print(f"[3/6] figure: {relative(svg)}")
    print(f"      registered output sha256: {registered['decay_fit.svg']['sha256']}")

    manifest_path = BUILD / "figures" / "manifest.json"
    dump_json(
        manifest_path,
        {
            "schema_version": "1.0",
            "figures": [
                {
                    "figure_id": "toy-decay-fit",
                    "run_id": run_id,
                    "claim": (
                        "The fitted curve reproduces the measured decay within the "
                        "residual scale of the dataset."
                    ),
                    "data_source": relative(predictions),
                    "result_source": relative(run_dir / "artifacts" / "metrics.json"),
                    "script": relative(CODE),
                    "figure_contract": relative(CONTRACT),
                    "reference_bundle": None,
                    "output_png": relative(png) if png is not None else relative(svg),
                    "output_svg": relative(svg),
                    "output_pdf": None,
                    "verification_status": "unverified",
                }
            ],
        },
    )
    print(f"      manifest: {relative(manifest_path)}")
    return manifest_path


def step_claim(record: dict, metrics: dict, figure_manifest: Path) -> Path:
    registry = BUILD / "paper" / "claim_registry.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    figures = load_json(figure_manifest).get("figures", [])
    # supporting_figures/supporting_tables/supporting_sources are resolved as
    # filesystem paths by check_registry, so register the rendered artifact.
    figure_paths = [str(item["output_svg"]) for item in figures if item.get("output_svg")]
    entry = {
        "claim_id": "C0000001",
        "paper_section": "results",
        "claim": (
            "For the synthetic decay dataset the baseline estimates "
            f"k = {metrics['k']} 1/s with rmse = {metrics['rmse']} V."
        ),
        "type": "result",
        "supporting_run_ids": [str(record["run_id"])],
        "supporting_figures": figure_paths,
        "supporting_tables": [],
        "supporting_sources": [],
        "confidence": "medium",
        "status": "draft",
    }
    registry.write_text(
        json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[4/6] claim: {entry['claim_id']} -> run {record['run_id']}")
    print(f"      registry: {relative(registry)}")
    print(f"      figure manifest: {relative(figure_manifest)}")
    return registry


def step_verify(record: dict, run_dir: Path, registry: Path) -> list[str]:
    problems: list[str] = []
    problems.extend(
        f"run record: {item}" for item in validate_run_record(record, run_dir, root=ROOT)
    )
    problems.extend(
        f"claim registry: {item}"
        for item in check_registry(registry, runs_root=RUNS, root=ROOT)
    )
    figure_manifest = BUILD / "figures" / "manifest.json"
    figures = load_json(figure_manifest).get("figures", [])
    for figure in figures:
        for key in ("output_png", "output_svg"):
            value = figure.get(key)
            if not value:
                continue
            target = ROOT / value
            if not target.is_file():
                problems.append(f"figure output is missing: {value}")
        script = ROOT / str(figure["script"])
        if not script.is_file():
            problems.append(f"figure script is missing: {figure['script']}")
        if str(figure["script"]) not in record.get("code_hashes", {}):
            problems.append(
                f"figure script {figure['script']} is not hashed in the run record"
            )
    registered = {Path(entry["path"]).name: entry["sha256"] for entry in record["outputs"]}
    for entry in figures:
        svg_value = entry.get("output_svg")
        if not svg_value:
            continue
        svg = ROOT / str(svg_value)
        if not svg.is_file():
            problems.append(f"figure output is missing: {svg_value}")
            continue
        declared = registered.get(svg.name)
        if declared is None:
            problems.append(f"figure {svg.name} is not a registered output of the run")
        elif declared != sha256_file(svg):
            problems.append(f"figure bytes no longer match the run record hash: {svg_value}")
    print(f"[5/6] verification: {'PASS' if not problems else 'FAIL'}")
    for item in problems:
        print(f"      - {item}")
    return problems


def step_paper(metrics: dict, record: dict, run_dir: Path) -> Path:
    fragment = BUILD / "paper" / "fragment.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    run_relative = run_dir.relative_to(ROOT).as_posix()
    fragment.write_text(
        "\n".join(
            [
                "# Paper fragment (toy demo)",
                "",
                "## Results",
                "",
                f"The decay rate of the synthetic series is estimated as "
                f"$k = {metrics['k']}$ s$^{{-1}}$ "
                f"(offset $c = {metrics['c']}$ V, amplitude $a = {metrics['a']}$ V), "
                f"with a root-mean-square residual of {metrics['rmse']} V over "
                f"{metrics['n_observations']} observations.",
                "",
                "![Fitted decay](figures/decay_fit.svg)",
                "",
                "## Provenance",
                "",
                f"* run: `{record['run_id']}` (`{run_relative}/manifest.json`)",
                "* claim: `C0000001` in `paper/claim_registry.jsonl`",
                f"* code: `{relative(CODE)}`",
                f"* data: `{relative(DATA)}`",
                "",
                "Every number above is copied from `metrics.json`, which the run record "
                "hashes. No number in this fragment was typed by hand.",
                "",
                "Status: demo fragment, not a submission and not independently verified.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[6/6] paper fragment: {relative(fragment)}")
    return fragment


def check_existing_build() -> list[str]:
    """Re-verify an existing demo build without running anything."""
    problems: list[str] = []
    if not RUNS.is_dir():
        return [f"no demo build found at {relative(BUILD)}; run the demo first"]
    run_dirs = sorted(path for path in RUNS.iterdir() if (path / "manifest.json").is_file())
    if not run_dirs:
        return [f"no run record found under {relative(RUNS)}"]
    run_dir = run_dirs[-1]
    record = load_json(run_dir / "manifest.json")
    problems.extend(
        f"run record: {item}" for item in validate_run_record(record, run_dir, root=ROOT)
    )
    registry = BUILD / "paper" / "claim_registry.jsonl"
    if not registry.is_file():
        problems.append(f"claim registry is missing: {relative(registry)}")
    else:
        problems.extend(
            f"claim registry: {item}"
            for item in check_registry(registry, runs_root=RUNS, root=ROOT)
        )
    figure_manifest = BUILD / "figures" / "manifest.json"
    if not figure_manifest.is_file():
        problems.append(f"figure manifest is missing: {relative(figure_manifest)}")
    else:
        for figure in load_json(figure_manifest).get("figures", []):
            if str(figure.get("script")) not in record.get("code_hashes", {}):
                problems.append(
                    f"figure script {figure.get('script')} is not hashed in the run record"
                )
            for key in ("output_png", "output_svg"):
                value = figure.get(key)
                if value and not (ROOT / str(value)).is_file():
                    problems.append(f"figure output is missing: {value}")
            svg_value = figure.get("output_svg")
            if svg_value:
                registered = {
                    Path(entry["path"]).name: entry["sha256"] for entry in record["outputs"]
                }
                svg = ROOT / str(svg_value)
                if svg.is_file() and registered.get(svg.name) != sha256_file(svg):
                    problems.append("figure bytes no longer match the run record hash")
                if not svg.is_file():
                    problems.append(f"figure output is missing: {svg_value}")
    fragment = BUILD / "paper" / "fragment.md"
    if not fragment.is_file():
        problems.append(f"paper fragment is missing: {relative(fragment)}")
    else:
        metrics = load_json(run_dir / "artifacts" / "metrics.json")
        text = fragment.read_text(encoding="utf-8")
        if str(metrics["rmse"]) not in text or str(metrics["k"]) not in text:
            problems.append("the paper fragment does not quote the registered metrics")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-build", action="store_true", help="Reuse the existing build dir.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify an existing demo build instead of re-running it.",
    )
    args = parser.parse_args()

    check_environment()
    if args.check_only:
        problems = check_existing_build()
        if not problems:
            print("demo check: PASS (existing build still matches its run record)")
            return 0
        print("demo check: FAIL")
        for item in problems:
            print(f"  - {item}")
        return 1

    if BUILD.exists() and not args.keep_build:
        shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    config = CONFIG
    digest = step_data()
    record, metrics, run_dir = step_run(config)
    figure_manifest = step_figure(record, metrics, run_dir)
    registry = step_claim(record, metrics, figure_manifest)
    problems = step_verify(record, run_dir, registry)
    fragment = step_paper(metrics, record, run_dir)

    summary = {
        "dataset_sha256": digest,
        "run_id": record["run_id"],
        "metrics": metrics,
        "run_dir": relative(run_dir),
        "figure_manifest": relative(figure_manifest),
        "claim_registry": relative(registry),
        "paper_fragment": relative(fragment),
        "problems": problems,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("")
        print("demo: " + ("PASS" if not problems else "FAIL"))
        print(f"  dataset -> run -> figure -> claim -> paper: {relative(BUILD)}")
        print("  Gate status: untouched. No human approval was recorded or implied.")
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as error:
        print(f"demo: FAIL\n  {error}\n{SETUP_HINT}", file=sys.stderr)
        raise SystemExit(2) from None
