"""Load only the app's OpenAI settings from its Git-ignored local secret file."""
import os
from pathlib import Path
import tomllib


def load_private_settings(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    path = root / '.streamlit/secrets.toml'
    if not path.exists():
        return
    with path.open('rb') as stream:
        settings = tomllib.load(stream)
    for name in ['OPENAI_API_KEY', 'OPENAI_MODEL']:
        if not os.environ.get(name) and isinstance(settings.get(name), str):
            os.environ[name] = settings[name]
