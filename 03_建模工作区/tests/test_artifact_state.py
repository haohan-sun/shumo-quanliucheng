import json

import pytest
from scripts.artifact_state import (
    GATE_DEPENDENCIES,
    invalidate,
    invalidate_manifest,
    recover,
    snapshot,
    sync_manifest,
)


def test_content_change_propagates_and_invalidates_pass(tmp_path):
    artifact = tmp_path / 'model.txt'
    artifact.write_text('v1')
    state = tmp_path / 'state.json'
    snapshot('G3', ['model.txt'], path=state, root=tmp_path)
    assert invalidate(state, root=tmp_path) == []
    artifact.touch()
    assert invalidate(state, root=tmp_path) == []
    artifact.write_text('v2')
    manifest = {'stages': [{'name': f'G{i} gate', 'status': 'approved'} for i in range(3, 8)]}
    reasons = invalidate_manifest(manifest, path=state, root=tmp_path)
    assert len(reasons) == 5
    assert all(stage['status'] == 'pending' for stage in manifest['stages'])
    assert json.loads(state.read_text(encoding='utf-8'))['snapshots']['G3']['hashes']['model.txt']


def test_reset_requires_external_human_record_and_paths_stay_inside(tmp_path):
    state = tmp_path / 'state.json'
    snapshot('G3', path=state, root=tmp_path)
    with pytest.raises(ValueError, match='human approval'):
        snapshot('G3', path=state, root=tmp_path)
    with pytest.raises(ValueError, match='human approval'):
        recover('G3', path=state, root=tmp_path)
    with pytest.raises(ValueError, match='outside project'):
        snapshot('G4', ['../outside'], path=state, root=tmp_path)


def test_directory_addition_deletion_invalidates(tmp_path):
    folder = tmp_path / 'data'
    folder.mkdir()
    state = tmp_path / 'state.json'
    snapshot('G5', ['data'], path=state, root=tmp_path)
    (folder / 'new.txt').write_text('new')
    assert invalidate(state, root=tmp_path)


def test_g2_change_invalidates_all_later_gates(tmp_path):
    route_tree = tmp_path / 'route.json'
    route_tree.write_text('v1')
    state = tmp_path / 'state.json'
    snapshot('G2', ['route.json'], path=state, root=tmp_path)
    route_tree.write_text('v2')
    stale = invalidate(state, root=tmp_path)
    assert [item.split(':', 1)[0] for item in stale] == ['G2','G3','G4','G5','G6','G7']


def test_problem_decision_change_invalidates_g1_and_every_downstream_gate(tmp_path):
    decision = tmp_path / '03_建模工作区/decisions/DECISION_LOG.md'
    decision.parent.mkdir(parents=True)
    decision.write_text('selected: A', encoding='utf-8')
    state = tmp_path / 'state.json'
    snapshot('G1', path=state, root=tmp_path)
    decision.write_text('selected: B', encoding='utf-8')
    stale = invalidate(state, root=tmp_path)
    assert [item.split(':', 1)[0] for item in stale] == [
        'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7'
    ]


def test_submission_gate_binds_all_submission_truth_sources():
    assert {
        '04_论文与提交/paper',
        '04_论文与提交/references',
        '04_论文与提交/ai_provenance/AI_USAGE_SUBMISSION.md',
        '90_工具与配置/configs/contest.yaml',
        '90_工具与配置/reports/verify.json',
    }.issubset(GATE_DEPENDENCIES['G7'])


def test_lifecycle_sync_captures_human_pass_then_invalidates_all_downstream(tmp_path):
    spec = tmp_path / '03_建模工作区/model/MODEL_SPEC.md'
    spec.parent.mkdir(parents=True)
    spec.write_text('v1')
    (tmp_path / '03_建模工作区/src').mkdir(parents=True)
    state = tmp_path / 'state.json'
    manifest = {'stages': [
        {'name': f'G{i} gate', 'status': 'approved', 'approved_by': 'human user',
         'approved_at': '2026-09-05T12:00:00+08:00'} for i in range(3, 8)],
        'stale_artifacts': []}
    assert sync_manifest(manifest, path=state, root=tmp_path) == []
    assert set(json.loads(state.read_text(encoding='utf-8'))['snapshots']) == {'G3','G4','G5','G6','G7'}
    spec.write_text('v2')
    stale = sync_manifest(manifest, path=state, root=tmp_path)
    assert len(stale) == 5
    assert all(stage['status'] == 'pending' for stage in manifest['stages'])
    assert manifest['stale_artifacts']
    for stage in manifest['stages']:
        stage.update(status='approved', approved_at='2026-09-05T13:00:00+08:00')
    assert sync_manifest(manifest, path=state, root=tmp_path) == []
    assert all(stage['status'] == 'approved' for stage in manifest['stages'])
