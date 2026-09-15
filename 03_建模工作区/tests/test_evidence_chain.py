import json
from pathlib import Path

import jsonschema

from scripts._project import sha256_file
from scripts.validate_contracts import artifact_run_link_errors

ROOT = Path(__file__).resolve().parents[2]


def test_result_schema_requires_run_and_artifact_hash():
    schema = json.loads((ROOT / '90_工具与配置/schemas/results.schema.json')
                        .read_text(encoding='utf-8'))
    result = {
        'schema_version': '1.0', 'generated_at': None,
        'results': [{'result_id': 'R1', 'experiment_id': 'E1', 'claim': 'x',
                     'value': 1, 'unit': None, 'artifact_path': 'x.json',
                     'verification_status': 'unverified'}],
    }
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(result))
    assert any('run_id' in error.message for error in errors)
    assert any('artifact_sha256' in error.message for error in errors)


def test_artifact_must_be_a_byte_identical_run_output(tmp_path):
    artifact = tmp_path / 'result.json'
    artifact.write_text('{"value":1}', encoding='utf-8')
    digest = sha256_file(artifact)
    run_id = '20260905T010203Z-abcdef12'
    records = {run_id: {'outputs': [{'path': 'artifacts/result.json', 'sha256': digest}]}}
    assert artifact_run_link_errors(
        label='result', run_id=run_id, artifact=artifact, declared_sha256=digest,
        run_records=records, root=tmp_path,
    ) == []
    artifact.write_text('{"value":2}', encoding='utf-8')
    errors = artifact_run_link_errors(
        label='result', run_id=run_id, artifact=artifact, declared_sha256=digest,
        run_records=records, root=tmp_path,
    )
    assert any('does not match' in error for error in errors)
    assert any('not a hashed output' in error for error in errors)
