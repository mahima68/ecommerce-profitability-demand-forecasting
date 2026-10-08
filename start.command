#!/bin/zsh
set -e
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"
if [[ -x "$project_dir/.venv/bin/python" ]]; then
  runtime="$project_dir/.venv/bin/python"
elif [[ -x "$project_dir/../../.venv/bin/python" ]]; then
  runtime="$project_dir/../../.venv/bin/python"
else
  echo "Create the Python environment using README.md, then run this launcher again."
  read -r "reply?Press Enter to close."
  exit 1
fi
echo "Opening Retail Decisions at http://127.0.0.1:8501"
if "$runtime" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)" >/dev/null 2>&1; then
  open 'http://127.0.0.1:8501'
  exit 0
fi
open 'http://127.0.0.1:8501'
exec "$runtime" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
