
from scripts.claim_registry import add_claim, check_registry
from scripts.run_record import add_output, create_run, finalize_run


def test_claim_to_run_to_artifact_chain(tmp_path):
    source = tmp_path / 'data.txt'
    source.write_text('3')
    code = tmp_path / 'example.py'
    code.write_text('print(6)')
    run = create_run({}, {'main': 1}, ['python', 'example.py'], runs_root=tmp_path / 'runs',
                     inputs=[source], code_paths=[code], root=tmp_path)
    result = run['dir'] / 'tables/value.txt'
    result.write_text('6')
    add_output(run, result, 'table')
    finalize_run(run, metrics={'value': 6, 'exit_code': 0, 'timed_out': False},
                 runtime_seconds=0.01)
    registry = tmp_path / 'claims.jsonl'
    add_claim('Results', 'value is 6', 'result', supporting_run_ids=[run['record']['run_id']], path=registry)
    assert check_registry(registry, runs_root=tmp_path / 'runs', root=tmp_path) == []
    result.write_text('7')
    assert any('output changed' in e for e in check_registry(registry, runs_root=tmp_path / 'runs', root=tmp_path))


def test_malformed_claim_returns_errors_not_crash(tmp_path):
    registry = tmp_path / 'claims.jsonl'
    registry.write_text('{}\ninvalid json\n')
    errors = check_registry(registry, root=tmp_path)
    assert any('unknown status' in e for e in errors)
    assert any('invalid JSON' in e for e in errors)


def test_result_claim_cannot_use_external_url_instead_of_run(tmp_path):
    registry = tmp_path / 'claims.jsonl'
    add_claim('Results', 'our model improves 50%', 'result',
              supporting_sources=['https://example.com'], path=registry)
    assert any('requires a supporting run_id' in error for error in
               check_registry(registry, runs_root=tmp_path / 'runs', root=tmp_path))


def test_bookkeeping_only_run_cannot_support_computational_claim(tmp_path):
    run = create_run({}, {}, ['python', '-c', 'print(1)'], runs_root=tmp_path / 'runs',
                     root=tmp_path)
    finalize_run(run)
    registry = tmp_path / 'claims.jsonl'
    add_claim('Results', 'value is 1', 'result',
              supporting_run_ids=[run['record']['run_id']], path=registry)
    errors = check_registry(registry, runs_root=tmp_path / 'runs', root=tmp_path)
    assert any('no hashed code' in error for error in errors)
    assert any('no hashed outputs' in error for error in errors)
    assert any('successful tracked execution' in error for error in errors)
