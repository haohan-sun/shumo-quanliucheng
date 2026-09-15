import json

import pytest

from scripts.run_record import create_run, add_output, finalize_run, validate_run_record


def make_run(tmp_path):
    source = tmp_path / 'input.txt'
    source.write_text('3')
    code = tmp_path / 'calc.py'
    code.write_text('print(3 * 2)')
    run = create_run({'factor': 2}, {'main': 42}, ['python', 'calc.py'],
                     runs_root=tmp_path / 'runs', inputs=[source], code_paths=[code], root=tmp_path)
    output = run['dir'] / 'tables/result.txt'
    output.write_text('6')
    add_output(run, output, 'table')
    finalize_run(run, metrics={'value': 6}, runtime_seconds=0.01)
    return run


def test_reproducibility_binding_and_output_tamper(tmp_path):
    run = make_run(tmp_path)
    assert validate_run_record(run['record'], run['dir'], root=tmp_path) == []
    (run['dir'] / 'tables/result.txt').write_text('7')
    assert any('output changed' in e for e in validate_run_record(run['record'], run['dir'], root=tmp_path))


def test_input_code_config_changes_are_detected(tmp_path):
    run = make_run(tmp_path)
    (tmp_path / 'input.txt').write_text('4')
    (tmp_path / 'calc.py').write_text('print(8)')
    run['record']['config']['factor'] = 3
    errors = validate_run_record(run['record'], run['dir'], root=tmp_path)
    assert any('input_hashes' in e for e in errors)
    assert any('code_hashes' in e for e in errors)
    assert any('config' in e for e in errors)


def test_run_immutable_and_output_traversal_rejected(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(ValueError, match='immutable'):
        finalize_run(run)
    run['record']['outputs'][0]['path'] = '../outside.txt'
    assert any('outside project' in e for e in validate_run_record(run['record'], run['dir'], root=tmp_path))
