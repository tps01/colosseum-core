#!/usr/bin/env sh

# Create/update and activate the Colosseum development virtual environment.
#
# Usage:
#   . ./scripts/start_environment.sh
#
# Environment overrides:
#   PYTHON=python3.12 VENV_PATH=/path/to/.venv SKIP_DEV=1

SCRIPT_PATH=${BASH_SOURCE:-$0}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)
if [ ! -f "$SCRIPT_DIR/start_environment.sh" ] && [ -f "./scripts/start_environment.sh" ]; then
    SCRIPT_DIR=$(CDPATH= cd -- "./scripts" && pwd)
fi
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PYTHON_BIN=${PYTHON:-python3}
VENV_ROOT=${VENV_PATH:-"$REPO_ROOT/.venv"}
SKIP_DEV=${SKIP_DEV:-0}

if ! cd "$REPO_ROOT"; then
    echo "Failed to change to repository root: $REPO_ROOT" >&2
    return 1 2>/dev/null || exit 1
fi

if [ ! -d "$VENV_ROOT" ]; then
    echo "Creating virtual environment: $VENV_ROOT"
    if ! "$PYTHON_BIN" -m venv "$VENV_ROOT"; then
        echo "Failed to create virtual environment with: $PYTHON_BIN" >&2
        return 1 2>/dev/null || exit 1
    fi
fi

VENV_PYTHON="$VENV_ROOT/bin/python"
ACTIVATE_SCRIPT="$VENV_ROOT/bin/activate"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Virtual environment Python was not found: $VENV_PYTHON" >&2
    return 1 2>/dev/null || exit 1
fi

if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "Virtual environment activation script was not found: $ACTIVATE_SCRIPT" >&2
    return 1 2>/dev/null || exit 1
fi

PYTHON_VERSION=$("$VENV_PYTHON" --version 2>&1 | sed 's/^Python //')
if ! "$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "Colosseum requires Python >=3.9; found $PYTHON_VERSION" >&2
    return 1 2>/dev/null || exit 1
fi
echo "Using Python $PYTHON_VERSION"

echo "Installing/updating build tooling..."
if ! "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel; then
    echo "Failed to install/update build tooling." >&2
    return 1 2>/dev/null || exit 1
fi

echo "Installing editable project: ."
if ! "$VENV_PYTHON" -m pip install --editable .; then
    echo "Failed to install editable project." >&2
    return 1 2>/dev/null || exit 1
fi

if [ "$SKIP_DEV" != "1" ]; then
    echo "Installing dev requirements: requirements-dev.txt"
    if ! "$VENV_PYTHON" -m pip install -r "$REPO_ROOT/requirements-dev.txt"; then
        echo "Failed to install dev requirements." >&2
        return 1 2>/dev/null || exit 1
    fi
fi

# shellcheck source=/dev/null
. "$ACTIVATE_SCRIPT"

echo
echo "Activated Colosseum environment at $VENV_ROOT"
echo "To keep activation in your current shell, run:"
echo "  . ./scripts/start_environment.sh"

return 0 2>/dev/null || exit 0
