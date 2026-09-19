#!/usr/bin/env bash
# Cloud Agent setup script for the "learning" polyglot repo.
#
# Used as BOTH `install` (bakes deps + warms the persistent $HOME caches into
# the environment build) and `start` (restores deps on every boot, since the
# boot-time git checkout re-creates /workspace and drops the baked venv and
# node_modules). It is idempotent and fast when dependencies are already
# present, and rebuilds quickly from the warm pip/npm/go caches when they are
# not.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- System dependency: Python venv support (absent from the base image) ---
if ! dpkg -s python3.12-venv >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends python3.12-venv python3-dev
fi

# --- Python: repo-root virtualenv (the "learningenv" convention from README) ---
if [ ! -x learningenv/bin/python ]; then
  python3 -m venv learningenv
fi
# shellcheck disable=SC1091
source learningenv/bin/activate
# Skip the (slower) dependency resolution when the venv already has the core
# packages; otherwise install everything (fast from the warm pip cache).
if ! python -c "import fastapi, uvicorn, torch, numpy, sklearn" >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  pip install \
    -r concepts/system-design/REST/ResponseCodeExamples/requirements.txt \
    -r concepts/system-design/REST/RequestVerbExamples/requirements.txt \
    -r concepts/system-design/webaApiCompression/requirements.txt \
    -r concepts/system-design/ProtocolBufferExample/requirements.txt \
    -r concepts/ai/machine-learning/requirements.txt
fi
deactivate

# --- Frontend: React app deps (CRA + TypeScript 5 requires legacy peer deps) ---
if [ ! -x frontend/react-based/concept-app/node_modules/.bin/react-scripts ]; then
  npm --prefix frontend/react-based/concept-app install --legacy-peer-deps
fi

# --- Go: rate-limiting module (stdlib only; warms module/build cache) ---
( cd concepts/system-design/rate-limiting/algorithms/go && go mod download && go build ./... )

echo "Setup complete."
