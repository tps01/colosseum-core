#!/bin/sh
# Create .venv in this bundle directory and install colosseum from local wheels.
set -eu

cd "$(dirname "$0")"

if [ ! -f VERSION ] || [ ! -f PYTHON_MINOR ]; then
  echo "ERROR: missing VERSION or PYTHON_MINOR in $(pwd)" >&2
  exit 1
fi

VERSION=$(tr -d '\r\n' < VERSION)
PY_MINOR=$(tr -d '\r\n' < PYTHON_MINOR)
VENV_DIR="${VENV_DIR:-.venv}"

if command -v "python${PY_MINOR}" >/dev/null 2>&1; then
  PYTHON="python${PY_MINOR}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "ERROR: python${PY_MINOR} or python3 not found (bundle expects Python ${PY_MINOR})" >&2
  exit 1
fi

echo "Using ${PYTHON} to create ${VENV_DIR} and install colosseum==${VERSION} ..."
"${PYTHON}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --no-index --find-links=wheels "colosseum==${VERSION}"

echo ""
echo "Installed colosseum ${VERSION}."
echo "Activate the environment:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "Smoke test:"
echo "  colosseum run smoke/run_sim.py --config smoke/bench.sim.toml"
