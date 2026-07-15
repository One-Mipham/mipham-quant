#!/usr/bin/env python3
"""
Build script for Mipham Quant Backend (PyInstaller one-file binary).

Usage:
    python build.py          # Build for current platform
    python build.py --clean  # Clean build
"""

import os
import shutil
import subprocess
import sys


def build():
    """Run PyInstaller to create a single-file backend binary."""
    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pyinstaller.spec")

    if not os.path.exists(spec_file):
        print("pyinstaller.spec not found. Generating...")
        _generate_spec()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file,
    ]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    # Copy binary to dist/
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
    os.makedirs(dist_dir, exist_ok=True)

    binary_name = "mipham-quant-backend"
    if sys.platform == "win32":
        binary_name += ".exe"
        src = os.path.join("dist", binary_name)
    else:
        src = os.path.join("dist", binary_name)

    if os.path.exists(src):
        dest = os.path.join(dist_dir, binary_name)
        shutil.copy2(src, dest)
        print(f"Binary copied to: {dest}")
        print(f"Size: {os.path.getsize(dest) / 1024 / 1024:.1f} MB")
    else:
        print(f"Binary not found at: {src}")


def _generate_spec():
    """Generate pyinstaller.spec file."""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all Flask blueprints and services
hiddenimports = collect_submodules('app')
hiddenimports += [
    'flask', 'flask_cors', 'werkzeug', 'jinja2',
    'numpy', 'pandas', 'ccxt', 'yfinance',
    'sqlite3', 'json', 'hashlib', 'cryptography',
    'requests', 'urllib3', 'certifi',
    'bcrypt', 'pyjwt', 'bip_utils',
    'akshare',
]

# Data files to bundle
datas = [
    ('migrations/init_sqlite.sql', 'migrations'),
]

# Try to add seed data
seed_path = os.path.join('app', 'data', 'seed.sql')
if os.path.exists(seed_path):
    datas.append((seed_path, os.path.join('app', 'data')))

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'PIL', 'scipy',
        'torch', 'tensorflow', 'sklearn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mipham-quant-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console for release builds (Windows)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    with open("pyinstaller.spec", "w") as f:
        f.write(spec_content)
    print("pyinstaller.spec generated")


if __name__ == "__main__":
    print("Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    build()
