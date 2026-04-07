"""Build script for Fluxo desktop application."""
from __future__ import annotations

import os
import platform
import subprocess
import sys


def build():
    system = platform.system()
    print(f"Building Fluxo for {system}...")

    base_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Fluxo",
        "--windowed",
        "--noconfirm",
        "--clean",
        "src/fluxo/app.py",
    ]

    if system == "Darwin":
        base_cmd.extend([
            "--osx-bundle-identifier", "com.dishine.fluxo",
        ])
    elif system == "Windows":
        base_cmd.extend([
            "--onefile",
        ])

    print(f"Running: {' '.join(base_cmd)}")
    subprocess.run(base_cmd, check=True)
    print("Build complete! Output in dist/")


if __name__ == "__main__":
    build()
