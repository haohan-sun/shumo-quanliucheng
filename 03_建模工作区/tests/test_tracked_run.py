from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from scripts.tracked_run import TIMEOUT_EXIT_CODE, execute_tracked


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "workspace"
    runs = root / "03_建模工作区" / "runs"
    runs.mkdir(parents=True)
    return root, runs


def _record(manifest: Path) -> dict:
    return json.loads(manifest.read_text(encoding="utf-8"))


def test_success_records_inputs_code_streams_and_output(tmp_path: Path) -> None:
    root, runs = _workspace(tmp_path)
    input_path = root / "input.txt"
    code_path = root / "program.py"
    output_path = root / "result.json"
    input_path.write_text("source", encoding="utf-8")
    code_path.write_text("print('source')", encoding="utf-8")
    command = [
        sys.executable,
        "-c",
        "from pathlib import Path; Path('result.json').write_text('{}'); print('ok')",
    ]

    exit_code, manifest = execute_tracked(
        command,
        config={"mode": "smoke"},
        seeds={"main": 7},
        inputs=[input_path],
        code_paths=[code_path],
        outputs=[(output_path, "metrics")],
        root=root,
        runs_root=runs,
    )

    record = _record(manifest)
    assert exit_code == 0
    assert record["metrics"] == {"exit_code": 0, "timed_out": False}
    assert set(record["input_hashes"]) == {"input.txt"}
    assert set(record["code_hashes"]) == {"program.py"}
    assert {item["kind"] for item in record["outputs"]} == {"stdout", "stderr", "metrics"}
    assert "ok" in (manifest.parent / "stdout.log").read_text(encoding="utf-8")
    assert not (manifest.parent / "manifest.pending.json").exists()


def test_failure_is_finalized_and_returns_child_code(tmp_path: Path) -> None:
    root, runs = _workspace(tmp_path)
    exit_code, manifest = execute_tracked(
        [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(9)"],
        root=root,
        runs_root=runs,
    )
    record = _record(manifest)
    assert exit_code == 9
    assert record["metrics"]["exit_code"] == 9
    assert "bad" in (manifest.parent / "stderr.log").read_text(encoding="utf-8")


def test_timeout_is_finalized_with_portable_timeout_code(tmp_path: Path) -> None:
    root, runs = _workspace(tmp_path)
    exit_code, manifest = execute_tracked(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout=0.05,
        root=root,
        runs_root=runs,
    )
    record = _record(manifest)
    assert exit_code == TIMEOUT_EXIT_CODE
    assert record["metrics"]["timed_out"] is True
    assert "timed out" in (manifest.parent / "stderr.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("field", ["cwd", "inputs", "code_paths", "outputs", "runs_root"])
def test_rejects_paths_outside_workspace(tmp_path: Path, field: str) -> None:
    root, runs = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    kwargs = {"root": root, "runs_root": runs}
    if field == "cwd":
        kwargs[field] = tmp_path
    elif field == "outputs":
        kwargs[field] = [outside]
    else:
        kwargs[field] = [outside] if field != "runs_root" else tmp_path / "runs"
    with pytest.raises(ValueError, match="outside project"):
        execute_tracked([sys.executable, "-c", "pass"], **kwargs)
