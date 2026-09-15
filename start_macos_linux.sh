#!/usr/bin/env bash
# Run with: bash start_macos_linux.sh [--port 8001] [--no-browser]
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  printf 'Run bash setup_macos_linux.sh first. See README.md.\n' >&2
  exit 1
fi
if [[ ! -f run.py ]]; then
  printf 'Required files are missing. Extract the entire ZIP first.\n' >&2
  exit 1
fi
printf '\nStarting SiteCare. Keep this terminal open. Press Ctrl+C to stop.\n'
exec .venv/bin/python run.py "$@"
