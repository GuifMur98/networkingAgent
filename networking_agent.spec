# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for NetworkingAgent Enterprise standalone executable."""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
PROJECT_ROOT = Path(os.path.abspath(SPEC)).parent

datas = [
    (str(PROJECT_ROOT / "src" / "networking_agent" / "tui" / "styles.tcss"), "networking_agent/tui"),
    (str(PROJECT_ROOT / "src" / "networking_agent" / "tui" / "styles.tcss"), "."),
    (str(PROJECT_ROOT / "docs" / "banner.png"), "docs"),
    (str(PROJECT_ROOT / "LICENSE"), "."),
    (str(PROJECT_ROOT / "README.md"), "."),
]
datas += collect_data_files("textual")
datas += collect_data_files("rich")
datas += collect_data_files("ntc_templates")

hiddenimports = [
    "cryptography",
    "cryptography.fernet",
    "jinja2",
    "jinja2.environment",
    "pydantic",
    "pydantic_settings",
    "sqlite3",
    "yaml",
    "ollama",
    "google.genai",
    "openai",
    "anthropic",
]
hiddenimports += collect_submodules("textual")
hiddenimports += collect_submodules("rich")
hiddenimports += collect_submodules("netmiko")
hiddenimports += collect_submodules("networking_agent")

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "torch", "scipy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="networking-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
