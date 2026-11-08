# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for NetworkingAgent Enterprise Setup Wizard executable."""

import os
from pathlib import Path

block_cipher = None
PROJECT_ROOT = Path(os.path.abspath(SPEC)).parent

# Bundled data payload: the standalone app executable, assets, and docs
datas = [
    (str(PROJECT_ROOT / "dist" / "networking-agent.exe"), "."),
    (str(PROJECT_ROOT / "assets"), "assets"),
    (str(PROJECT_ROOT / "README.md"), "."),
    (str(PROJECT_ROOT / "LICENSE"), "."),
]

hiddenimports = [
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.ttk",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "winreg",
]

a = Analysis(
    [str(PROJECT_ROOT / "scripts" / "installer_wizard.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "torch", "scipy", "textual", "rich", "netmiko", "jinja2"],
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
    name="NetworkingAgent-v2.1.1-Setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "assets" / "installer_icon.ico"),
)
