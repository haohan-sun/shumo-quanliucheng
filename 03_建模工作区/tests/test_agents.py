import json
import re
import tomllib
from pathlib import Path


def test_read_only_specialists():
    root = Path(__file__).resolve().parents[2]
    for name in ('validator', 'replicator', 'judge'):
        path = root / f'90_工具与配置/.codex/agents/{name}.toml'
        data = tomllib.loads(path.read_text(encoding='utf-8'))
        assert data['name'] == name
        assert data['sandbox_mode'] == 'read-only'
        text = (data['description'] + data['developer_instructions']).lower()
        assert 'gate' in text and ('never' in text or '不得' in text)


def test_only_one_visual_policy_claims_authority():
    root = Path(__file__).resolve().parents[2]
    canonical = root / '90_工具与配置/configs/VISUAL_STYLE_GUIDE.md'
    assert 'ONLY authoritative visual policy' in canonical.read_text(encoding='utf-8')


def test_deriver_is_scoped_workspace_writer():
    root = Path(__file__).resolve().parents[2]
    path = root / '90_工具与配置/.codex/agents/deriver.toml'
    data = tomllib.loads(path.read_text(encoding='utf-8'))
    assert data['name'] == 'deriver'
    assert data['sandbox_mode'] == 'workspace-write'
    text = (data['description'] + data['developer_instructions']).lower()
    assert '03_建模工作区/model/' in text
    assert 'never choose' in text and 'implementation code' in text


def test_hooks_are_workspace_portable():
    root = Path(__file__).resolve().parents[2]
    hooks = json.loads((root / '90_工具与配置/.codex/hooks.json').read_text(encoding='utf-8'))
    commands = [hook['commandWindows'] for groups in hooks['hooks'].values()
                for group in groups for hook in group['hooks']]
    assert commands and all(not re.search(r'[A-Za-z]:\\\\', command) for command in commands)
    assert all('lifecycle_hooks.py' in command for command in commands)
