#!/usr/bin/env python3
"""Build script for compiling NetworkingAgent Enterprise into a standalone binary."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "release-artifacts"


def check_prerequisites():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller

        print(f"[*] Found PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller is not installed. Installing via uv / pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.11.0"])


def clean_previous_builds():
    """Remove artifacts from previous builds."""
    print("[*] Cleaning previous build directories...")
    for d in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def build_binary():
    """Invoke PyInstaller using the project spec file."""
    print("[*] Compiling standalone executable with PyInstaller...")
    spec_path = PROJECT_ROOT / "networking_agent.spec"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path),
    ]
    subprocess.check_call(cmd, cwd=str(PROJECT_ROOT))


def package_artifacts():
    """Package the compiled executable into a distributable archive."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ["amd64", "x86_64"]:
        arch = "x64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    else:
        arch = machine

    version = "2.1.1"
    base_name = f"networking-agent-v{version}-{system}-{arch}"
    bundle_dir = RELEASE_DIR / base_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy binary
    if system == "windows":
        binary_src = DIST_DIR / "networking-agent.exe"
        binary_dst = bundle_dir / "networking-agent.exe"
    else:
        binary_src = DIST_DIR / "networking-agent"
        binary_dst = bundle_dir / "networking-agent"

    if not binary_src.exists():
        raise FileNotFoundError(f"Compiled binary not found at: {binary_src}")

    shutil.copy2(binary_src, binary_dst)
    if system != "windows":
        os.chmod(binary_dst, 0o755)

    # Copy documentation and licenses
    for doc in ["README.md", "LICENSE"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, bundle_dir / doc)

    # Copy assets (icons and logos)
    assets_src = PROJECT_ROOT / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, bundle_dir / "assets", dirs_exist_ok=True)

    # Copy scripts and launchers
    if system == "windows":
        iniciar_bat = (
            "@echo off\r\n"
            "title NetworkingAgent Enterprise v2.1.1\r\n"
            '"%~dp0networking-agent.exe" %*\r\n'
            "if %ERRORLEVEL% NEQ 0 (\r\n"
            "    echo.\r\n"
            "    echo [ERROR] NetworkingAgent se cerro con codigo de salida %ERRORLEVEL%.\r\n"
            "    pause\r\n"
            ")\r\n"
        )
        (bundle_dir / "iniciar.bat").write_text(iniciar_bat, encoding="ascii")

        instalar_bat = (
            "@echo off\r\n"
            "setlocal\r\n"
            "echo =================================================================\r\n"
            "echo   NetworkingAgent Enterprise v2.1.1 - Instalador para Windows\r\n"
            "echo =================================================================\r\n"
            "echo.\r\n"
            'powershell.exe -ExecutionPolicy Bypass -File "%~dp0install.ps1"\r\n'
            "echo.\r\n"
            "pause\r\n"
            "endlocal\r\n"
        )
        (bundle_dir / "instalar.bat").write_text(instalar_bat, encoding="ascii")

        if (PROJECT_ROOT / "install.ps1").exists():
            shutil.copy2(PROJECT_ROOT / "install.ps1", bundle_dir / "install.ps1")
    else:
        if (PROJECT_ROOT / "install.sh").exists():
            shutil.copy2(PROJECT_ROOT / "install.sh", bundle_dir / "install.sh")

    # Create archive
    print(f"[*] Creating release archive for {system}-{arch}...")
    if system == "windows":
        archive_path = RELEASE_DIR / f"{base_name}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(bundle_dir):
                for f in files:
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(RELEASE_DIR)
                    zf.write(file_path, arcname)
        print(f"[+] Windows standalone release package ready: {archive_path}")
    else:
        archive_path = RELEASE_DIR / f"{base_name}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(bundle_dir, arcname=base_name)
        print(f"[+] Posix standalone release package ready: {archive_path}")

    # Remove temporary uncompressed bundle dir
    shutil.rmtree(bundle_dir, ignore_errors=True)
    return archive_path


def main():
    print("=========================================================")
    print("   NetworkingAgent Enterprise - Standalone Build Tool   ")
    print("=========================================================")
    check_prerequisites()
    clean_previous_builds()
    build_binary()
    package_artifacts()
    print("[SUCCESS] Build and packaging complete.")


if __name__ == "__main__":
    main()
