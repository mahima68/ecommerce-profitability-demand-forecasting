"""User-operated local key entry; never print or transmit the entered key."""
import getpass
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import toml

ROOT = Path(__file__).resolve().parents[1]


def popup_key():
    script = '''text returned of (display dialog "Paste your OpenAI API key here. It stays private on this Mac." default answer "" with hidden answer buttons {"Cancel", "Save"} default button "Save" with title "Private AI setup")'''
    result = subprocess.run(['/usr/bin/osascript', '-e', script], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('Setup cancelled; nothing was saved.')
    return result.stdout.strip()


def save_settings(key, model, root=ROOT):
    folder = Path(root) / '.streamlit'
    folder.mkdir(exist_ok=True, parents=True)
    target = folder / 'secrets.toml'
    settings = toml.load(target) if target.exists() else {}
    settings.update(OPENAI_API_KEY=key, OPENAI_MODEL=model)
    fd, temp = tempfile.mkstemp(prefix='.secrets-', dir=folder)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(toml.dumps(settings))
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


if __name__ == '__main__':
    print('Private OpenAI setup. This step makes no API requests.')
    use_popup = '--popup' in sys.argv
    if use_popup:
        key = popup_key()
    else:
        print('Paste your key at the hidden prompt, then press Enter. No characters will appear.')
        key = getpass.getpass('API key (hidden): ').strip()
    if not key or any(c.isspace() for c in key):
        raise SystemExit('No valid key entered; nothing was saved.')
    model = 'gpt-5-mini' if use_popup else (input('Model [gpt-5-mini]: ').strip() or 'gpt-5-mini')
    save_settings(key, model)
    print('Saved privately. The key file is excluded from GitHub and project downloads.')
    print('Return to the chat and say: Key saved locally.')
