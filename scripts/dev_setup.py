#!/usr/bin/env python3
"""
Development setup script for PyAgent.

Creates a virtual environment and installs all packages in editable mode.
Usage:
    python scripts/dev_setup.py
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"

PACKAGES = [
    "packages/protocol",
    "packages/ai",
    "packages/agent",
    "packages/storage",
    "packages/coding_agent",
    "packages/tui",
    "packages/client",
    "packages/server",
    "packages/evals",
]


def main() -> None:
    print("=" * 60)
    print("PyAgent Development Setup")
    print("=" * 60)

    # Create virtual environment
    if not VENV_DIR.exists():
        print(f"\n[1/3] Creating virtual environment at {VENV_DIR}...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"\n[1/3] Virtual environment already exists at {VENV_DIR}")

    # Determine pip path
    if os.name == "nt":
        pip = str(VENV_DIR / "Scripts" / "pip")
        python = str(VENV_DIR / "Scripts" / "python")
    else:
        pip = str(VENV_DIR / "bin" / "pip")
        python = str(VENV_DIR / "bin" / "python")

    # Upgrade pip
    print("\n[2/3] Upgrading pip...")
    subprocess.check_call([python, "-m", "pip", "install", "--upgrade", "pip"])

    # Install packages in dependency order
    print("\n[3/3] Installing all packages in editable mode...")
    for pkg in PACKAGES:
        pkg_path = PROJECT_ROOT / pkg
        print(f"  -> {pkg}...")
        subprocess.check_call([pip, "install", "-e", str(pkg_path), "--quiet"])

    print("\n" + "=" * 60)
    print("Setup complete!")
    print(f"  Virtual env: {VENV_DIR}")
    print(f"  Activate:    {'Scripts' if os.name == 'nt' else 'bin'}/activate")
    print("\nTo run the agent:")
    print(f"  {python} -m pyagent_coding_agent --help")
    print("=" * 60)


if __name__ == "__main__":
    main()
