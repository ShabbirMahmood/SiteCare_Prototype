#!/usr/bin/env bash
# Run with: bash setup_macos_linux.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
trap 'printf "\nSetup stopped. Read the error above and README.md. Do not delete your data folder.\n" >&2' ERR
printf '\nSiteCare Prototype - First-time setup\n'
printf 'A private .venv is created here. Internet access is needed for packages.\n\n'
if [[ ! -f run.py || ! -f requirements.txt ]]; then
  printf 'Required files are missing. Extract the entire ZIP first.\n' >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  python_cmd=''
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
      python_cmd="$candidate"
      break
    fi
  done
  if [[ -z "$python_cmd" ]]; then
    printf 'Python 3.11 or newer was not found. Install Python 3.13, then retry.\n' >&2
    exit 1
  fi
  printf 'Creating .venv with %s ...\n' "$python_cmd"
  "$python_cmd" -m venv .venv
fi
.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
.venv/bin/python --version
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'import fastapi, uvicorn, multipart, PIL'
printf '\nSetup complete. Start with: bash start_macos_linux.sh\n'
