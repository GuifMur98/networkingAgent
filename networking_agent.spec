# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for NetworkingAgent Enterprise standalone executable."""

import os
from pathlib import Path

block_cipher = None
PROJECT_ROOT = Path(os.path.abspath(SPEC)).parent

datas = [
    (str(PROJECT_ROOT / "src" / "networking_agent" / "tui" / "styles.tcss"), "networking_agent/tui"),
    (str(PROJECT_ROOT / "docs" / "banner.png"), "docs"),
    (str(PROJECT_ROOT / "LICENSE"), "."),
    (str(PROJECT_ROOT / "README.md"), "."),
]

hiddenimports = [
    # Textual TUI and components
    "textual",
    "textual.app",
    "textual.binding",
    "textual.command",
    "textual.containers",
    "textual.events",
    "textual.geometry",
    "textual.message",
    "textual.screen",
    "textual.widget",
    "textual.widgets",
    "textual.widgets._footer",
    "textual.widgets._tabbed_content",
    "textual.widgets._text_area",
    "textual.widgets._data_table",
    "textual.widgets._selection_list",

    # Rich formatting
    "rich",
    "rich.panel",
    "rich.text",
    "rich.table",
    "rich.syntax",
    "rich.align",
    "rich.box",

    # Netmiko vendor drivers
    "netmiko",
    "netmiko.cisco",
    "netmiko.cisco.cisco_ios",
    "netmiko.cisco.cisco_nxos_ssh",
    "netmiko.cisco.cisco_xr",
    "netmiko.juniper",
    "netmiko.juniper.juniper",
    "netmiko.mikrotik",
    "netmiko.mikrotik.mikrotik_ssh",

    # Core & Cryptography
    "cryptography",
    "cryptography.fernet",
    "jinja2",
    "jinja2.environment",
    "pydantic",
    "pydantic_settings",
    "sqlite3",
    "yaml",

    # AI Brains connectors
    "ollama",
    "google.genai",
    "openai",
    "anthropic",
]

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
