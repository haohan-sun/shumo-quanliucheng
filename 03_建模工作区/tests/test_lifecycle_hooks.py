from scripts import lifecycle_hooks


def test_event_digest_accepts_structured_values_without_recording_content():
    record = lifecycle_hooks.event_record({
        'hook_event_name': 'Stop',
        'last_assistant_message': {'summary': 'private content'},
    })
    assert len(record['message_sha256']) == 64
    assert 'private content' not in str(record)


def test_stop_guard_is_small_and_targets_only_workflow_invariants(tmp_path):
    assert 1 <= len(lifecycle_hooks.STOP_GUARD_TESTS) <= 6
    assert all(path.startswith('03_建模工作区/tests/test_')
               for path in lifecycle_hooks.STOP_GUARD_TESTS)
    names = {path.rsplit('/', 1)[-1] for path in lifecycle_hooks.STOP_GUARD_TESTS}
    assert {'test_auto_routing.py', 'test_artifact_state.py', 'test_package_guard.py'} <= names


def test_stop_reentry_reports_findings_without_infinite_block(monkeypatch, tmp_path):
    monkeypatch.setattr(lifecycle_hooks, 'stop_checks', lambda root: (['broken'], True))
    result = lifecycle_hooks.stop({'stop_hook_active': True}, tmp_path)
    assert result['continue'] is True
    assert 'findings' in result['systemMessage']
