#!/usr/bin/env bash
# Development setup script for PyAgent (Unix/Git Bash)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "============================================================"
echo "PyAgent Development Setup"
echo "============================================================"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n[1/3] Creating virtual environment at $VENV_DIR..."
    python -m venv "$VENV_DIR"
else
    echo -e "\n[1/3] Virtual environment already exists at $VENV_DIR"
fi

# Determine pip path
if [ "$(uname -s)" = "Linux" ] || [ "$(uname -s)" = "Darwin" ]; then
    PIP="$VENV_DIR/bin/pip"
    PYTHON="$VENV_DIR/bin/python"
else
    PIP="$VENV_DIR/Scripts/pip"
    PYTHON="$VENV_DIR/Scripts/python"
fi

# Upgrade pip
echo -e "\n[2/3] Upgrading pip..."
"$PYTHON" -m pip install --upgrade pip

# Install packages in dependency order
PACKAGES="protocol ai agent storage coding_agent tui client server evals"
echo -e "\n[3/3] Installing all packages in editable mode..."
for pkg in $PACKAGES; do
    echo "  -> packages/$pkg..."
    "$PIP" install -e "$PROJECT_ROOT/packages/$pkg" --quiet
done

echo -e "\n============================================================"
echo "Setup complete!"
echo "  Virtual env: $VENV_DIR"
echo "  Activate:    source $VENV_DIR/Scripts/activate"
echo -e "\nTo run the agent:"
echo "  $PYTHON -m pyagent_coding_agent --help"
echo "============================================================"
