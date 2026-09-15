"""Data audit: schema/dtype/missing/duplicate/outlier/unit/leakage screening.

Produces a machine-readable report conforming to schemas/data-audit.schema.json.
Blocked findings must be resolved before MODEL_SPEC freezes (G3 input).

CLI:
    python .../data_audit.py --input data.csv --output audit.json [--target y] [--time col] [--lat lat --lon lon]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._project import ROOT, sha256_file


def _findings() -> list[dict[str, Any]]:
    return []


def _add(findings: list[dict[str, Any]], code: str, severity: str, column: str, message: str,
         n: int = 0, rows: list[int] | None = None) -> None:
    findings.append({"code": code, "severity": severity, "column": column, "message": message,
                     "n_affected": int(n), "example_rows": [int(value) for value in (rows or [])[:5]]})


def audit_dataframe(
    df: pd.DataFrame,
    *,
    target: str = "",
    time_col: str = "",
    lat: str = "",
    lon: str = "",
    source_name: str = "",
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    dictionary: list[dict[str, Any]] = []
    n = len(df)
    if n == 0:
        _add(findings, "SAMPLE_SUFFICIENCY", "blocking", "(rows)", "dataset is empty")
    for requested, role in ((target, "target"), (time_col, "time"), (lat, "latitude"), (lon, "longitude")):
        if requested and requested not in df.columns:
            _add(findings, "SCHEMA_MISMATCH", "blocking", requested,
                 f"declared {role} column is missing")

    for column in df.columns:
        series = df[column]
        missing = float(series.isna().mean())
        role = "target" if column == target else "unknown"
        if column == time_col:
            role = "time"
        elif column in {lat, lon}:
            role = "location"
        elif series.nunique(dropna=False) == n and n > 1:
            role = "identifier" if role == "unknown" else role
        dtype = str(series.dtype)
        dictionary.append({
            "column": str(column), "dtype": dtype, "role": role,
            "unit": "", "missing_rate": round(missing, 4),
            "n_unique": int(series.nunique(dropna=True)),
            "description": "",
        })
        if missing > 0.5:
            _add(findings, "MISSING_VALUES", "blocking", str(column),
                 f"{missing:.0%} missing exceeds 50%", int(series.isna().sum()))
        elif missing > 0:
            _add(findings, "MISSING_VALUES", "warning", str(column),
                 f"{missing:.1%} missing", int(series.isna().sum()))

        if pd.api.types.is_numeric_dtype(series):
            values = series.dropna()
            if len(values):
                q1, q3 = values.quantile([0.25, 0.75])
                iqr = q3 - q1
                outliers = values[(values < q1 - 3 * iqr) | (values > q3 + 3 * iqr)]
                if len(outliers):
                    _add(findings, "OUTLIER", "warning", str(column),
                         f"{len(outliers)} values beyond 3*IQR", len(outliers),
                         list(outliers.index[:5]))
                if (values <= 0).any() and str(column).lower().find("count") >= 0:
                    _add(findings, "IMPOSSIBLE_VALUE", "warning", str(column),
                         "count-like column contains non-positive values")
                if str(column).lower() in {"age", "percent", "ratio", "rate", "prob", "probability"}:
                    lo, hi = values.min(), values.max()
                    if str(column).lower() in {"percent"} and (lo < 0 or hi > 100):
                        _add(findings, "IMPOSSIBLE_VALUE", "warning", str(column),
                             "percent outside [0, 100]")
                    if str(column).lower() in {"prob", "probability"} and (lo < 0 or hi > 1):
                        _add(findings, "IMPOSSIBLE_VALUE", "warning", str(column),
                             "probability outside [0, 1]")

    dup_rows = int(df.duplicated().sum())
    if dup_rows:
        _add(findings, "DUPLICATE_ROWS", "warning", "(rows)",
             f"{dup_rows} fully duplicated rows", dup_rows, list(df.index[df.duplicated()][:5]))

    for column in df.columns:
        text = df[column].astype(str)
        if text.str.contains(r"[^\x00-\x7F]", regex=True).mean() > 0.8 and text.str.contains("ï¿½|Ã©|Ã¤", regex=True).any():
            _add(findings, "ENCODING_ISSUE", "warning", str(column), "mojibake patterns suggest wrong encoding decode")

    if time_col and time_col in df.columns:
        times = pd.to_datetime(df[time_col], errors="coerce")
        if times.isna().any():
            _add(findings, "TEMPORAL_ORDER", "warning", time_col,
                 f"{int(times.isna().sum())} unparseable timestamps")
        elif not times.is_monotonic_increasing:
            _add(findings, "TEMPORAL_ORDER", "info", time_col,
                 "timestamps not sorted ascending (note sampling order)")

    if lat and lon and lat in df.columns and lon in df.columns:
        la, lo = pd.to_numeric(df[lat], errors="coerce"), pd.to_numeric(df[lon], errors="coerce")
        bad = ((la.abs() > 90) | (lo.abs() > 180)).sum()
        if bad:
            _add(findings, "GEO_INCONSISTENCY", "blocking", f"{lat}/{lon}",
                 f"{int(bad)} coordinates outside valid ranges", int(bad))

    if target and target in df.columns:
        # label leakage heuristic: object columns whose text contains the target column name
        for column in df.columns:
            if column != target and df[column].dtype == object and target.lower() in str(column).lower():
                _add(findings, "LABEL_LEAKAGE", "warning", str(column),
                     f"feature name embeds target name {target!r}; verify pipeline timing")

    if n and n < 30:
        _add(findings, "SAMPLE_SUFFICIENCY", "warning", "(rows)",
             f"only {n} rows; report uncertainty explicitly")

    blocking = [f for f in findings if f["severity"] == "blocking"]
    verdict = "blocked" if blocking else ("usable_with_fixes" if findings else "usable")
    return {
        "schema_version": "1.0",
        "dataset": source_name,
        "data_dictionary": dictionary,
        "findings": findings,
        "preprocessing_contract": [],
        "rejected_assumptions": [],
        "unresolved_risks": [f["message"] for f in findings if f["severity"] == "warning"],
        "verdict": verdict,
    }


def audit_file(input_path: Path, **kwargs: Any) -> dict[str, Any]:
    if input_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(input_path)
    elif input_path.suffix.lower() == ".json":
        df = pd.read_json(input_path)
    else:
        for encoding in ("utf-8", "gbk", "latin-1"):
            try:
                df = pd.read_csv(input_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"cannot decode {input_path}")
    report = audit_dataframe(df, source_name=input_path.name, **kwargs)
    report["source_sha256"] = sha256_file(input_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a tabular dataset before modeling.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--target", default="")
    parser.add_argument("--time", dest="time_col", default="")
    parser.add_argument("--lat", default="")
    parser.add_argument("--lon", default="")
    args = parser.parse_args()
    report = audit_file(args.input, target=args.target, time_col=args.time_col,
                        lat=args.lat, lon=args.lon)
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output = args.output or ROOT / "03_建模工作区" / "data" / "audits" / f"{args.input.stem}.audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"verdict: {report['verdict']}  findings: {len(report['findings'])}  -> {output}")
    return 1 if report["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
