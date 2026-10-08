#!/bin/zsh
set -e
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"
if [[ -x "$project_dir/.venv/bin/python" ]]; then
  runtime="$project_dir/.venv/bin/python"
elif [[ -x "$project_dir/../../.venv/bin/python" ]]; then
  runtime="$project_dir/../../.venv/bin/python"
else
  echo "Set up the Python environment as described in README.md first."
  exit 1
fi
"$runtime" src/configure_ai.py --popup
read -r "reply?Press Enter to close."
