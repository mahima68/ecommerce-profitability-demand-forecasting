import os
import stat
from configure_ai import save_settings
from ecommerce.private_settings import load_private_settings


def test_private_file_permissions_and_loading(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    save_settings('dummy-not-a-real-key', 'test-model', root=tmp_path)
    path = tmp_path / '.streamlit/secrets.toml'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    load_private_settings(tmp_path)
    assert os.environ['OPENAI_API_KEY'] == 'dummy-not-a-real-key'
    assert os.environ['OPENAI_MODEL'] == 'test-model'


def test_environment_precedence_and_preservation(tmp_path, monkeypatch):
    folder = tmp_path / '.streamlit'
    folder.mkdir()
    (folder / 'secrets.toml').write_text('OTHER_SETTING = "keep"\n')
    save_settings('dummy-not-a-real-key', 'test-model', root=tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', 'existing-test-value')
    monkeypatch.setenv('OPENAI_MODEL', 'existing-model')
    load_private_settings(tmp_path)
    assert os.environ['OPENAI_API_KEY'] == 'existing-test-value'
    assert os.environ['OPENAI_MODEL'] == 'existing-model'
    assert 'OTHER_SETTING' in (folder / 'secrets.toml').read_text()
