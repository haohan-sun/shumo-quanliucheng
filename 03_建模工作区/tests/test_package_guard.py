from pathlib import Path
import zipfile
import pytest
from scripts import build_submission as build
from scripts.package_guard import assert_package_files, check_target, excluded, load_boundaries


@pytest.mark.parametrize('name', ['../paper.pdf', '/paper.pdf', 'C:/paper.pdf', '.git/config',
    'src/_locked_cache_copy/a.py', '_locked_cache_x/a', 'src/__pycache__/a.pyc',
    '~$paper.docx', 'src/_LOCKED_CACHE_COPY/a.py'])
def test_forbidden_names(name):
    assert excluded(name, load_boundaries())


def test_clean_names_and_external_directory(tmp_path):
    (tmp_path / 'paper.pdf').write_bytes(b'fixture')
    assert check_target(tmp_path, {'exclude_from_package': []}) == []
    assert_package_files([tmp_path / 'paper.pdf'], tmp_path)
    with pytest.raises(ValueError):
        assert_package_files([tmp_path.parent / 'outside.pdf'], tmp_path)


def test_zip_and_nested_locked_cache(tmp_path):
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as out:
        out.writestr('src/_locked_cache_x/private.json', '{}')
    assert len(check_target(archive)) == 1


def test_build_rejects_before_creating_archive(tmp_path, monkeypatch):
    (tmp_path / 'run-manifest.json').write_text('{}')
    source = tmp_path / 'src' / '_locked_cache_bad' / 'source.py'
    source.parent.mkdir(parents=True)
    source.write_text('secret')
    monkeypatch.setattr(build, 'valid_human_gate', lambda *a: True)
    monkeypatch.setattr(build, 'readiness_blockers', lambda *a: [])
    monkeypatch.setattr(build, 'package_files', lambda *a: [source])
    output = tmp_path / 'submission.zip'
    with pytest.raises(ValueError):
        build.build_archive(output, tmp_path)
    assert not output.exists()


def test_build_never_bypasses_g7(tmp_path):
    (tmp_path / 'run-manifest.json').write_text('{}')
    with pytest.raises(PermissionError):
        build.build_archive(tmp_path / 'submission.zip', tmp_path)


def test_visual_policy_single_source():
    root = Path(__file__).resolve().parents[2]
    for relative in ['90_工具与配置/画图SKILL.md', '90_工具与配置/configs/CODE_STYLE.md',
                     '03_建模工作区/src/viz/README.md']:
        assert 'VISUAL_STYLE_GUIDE.md' in (root / relative).read_text(encoding='utf-8')
