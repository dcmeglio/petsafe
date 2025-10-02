#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Unable to locate python interpreter '${PYTHON_BIN}'." >&2
  exit 1
fi

VENV_PATH="${VENV_PATH:-${REPO_ROOT}/.venv}"
if [ ! -d "${VENV_PATH}" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_PATH}"
fi

VENV_PYTHON="${VENV_PATH}/bin/python"

"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -e .
"${VENV_PYTHON}" -m pip install pytest pytest-asyncio
