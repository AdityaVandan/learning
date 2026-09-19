#!/usr/bin/env bash
# Cloud Agent install script for the "learning" polyglot repo.
# Idempotent: safe to run repeatedly. Prepares Python (learningenv venv),
# the React frontend, and the Go rate-limiting module.
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
python -m pip install --upgrade pip
pip install \
  -r concepts/system-design/REST/ResponseCodeExamples/requirements.txt \
  -r concepts/system-design/REST/RequestVerbExamples/requirements.txt \
  -r concepts/system-design/webaApiCompression/requirements.txt \
  -r concepts/system-design/ProtocolBufferExample/requirements.txt \
  -r concepts/ai/machine-learning/requirements.txt
deactivate

# --- Frontend: React app deps (CRA + TypeScript 5 requires legacy peer deps) ---
npm --prefix frontend/react-based/concept-app install --legacy-peer-deps

# --- Go: rate-limiting module (stdlib only; warms module/build cache) ---
( cd concepts/system-design/rate-limiting/algorithms/go && go mod download && go build ./... )

echo "Install complete."
