#!/bin/zsh
set -e
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"
if [[ -x "$project_dir/.venv/bin/python" ]]; then
  runtime="$project_dir/.venv/bin/python"
elif [[ -x "$project_dir/../../.venv/bin/python" ]]; then
  runtime="$project_dir/../../.venv/bin/python"
else
  echo "Set up Python as described in README.md first."
  exit 1
fi
echo "Loading this project's retail_portfolio schema into local Postgres.app."
"$runtime" src/load_postgres.py --local
read -r "reply?Finished. Press Enter to close."
