#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements/dev.txt
.venv/bin/pip freeze > requirements.lock.txt
.venv/bin/pre-commit install || true
echo "Bootstrap complete."
