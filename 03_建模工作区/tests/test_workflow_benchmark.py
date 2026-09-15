import importlib.util
from pathlib import Path


def test_minimal_workflow_benchmark():
    path = Path(__file__).resolve().parents[2] / '90_工具与配置/evals/workflow_benchmark.py'
    spec = importlib.util.spec_from_file_location('workflow_benchmark', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_benchmark(2)
    assert result['status'] == 'PASS'
    assert result['routing_operations'] == 14
    assert result['route_mismatches'] == []
