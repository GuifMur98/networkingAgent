#!/usr/bin/env python3
"""Build script for compiling NetworkingAgent Enterprise into standalone binaries and installers."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "release-artifacts"
VERSION = "2.1.1"


def check_prerequisites():
    """Ensure PyInstaller and Pillow are installed."""
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
    """Invoke PyInstaller using the project spec files."""
    system = platform.system().lower()
    spec_path = PROJECT_ROOT / "networking_agent.spec"

    print(f"[*] Compiling standalone application executable ({system})...")
    app_workpath = Path(tempfile.gettempdir()) / "pyi_work_app"
    if app_workpath.exists():
        shutil.rmtree(app_workpath, ignore_errors=True)

    cmd_app = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--workpath",
        str(app_workpath),
        str(spec_path),
    ]
    subprocess.check_call(cmd_app, cwd=str(PROJECT_ROOT))

    # On Windows, compile the single-file GUI Setup Wizard installer
    if system == "windows":
        installer_spec = PROJECT_ROOT / "installer.spec"
        print("[*] Compiling native Windows Setup Wizard (NetworkingAgent-Setup.exe)...")
        installer_workpath = Path(tempfile.gettempdir()) / "pyi_work_installer"
        if installer_workpath.exists():
            shutil.rmtree(installer_workpath, ignore_errors=True)

        cmd_installer = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--workpath",
            str(installer_workpath),
            str(installer_spec),
        ]
        subprocess.check_call(cmd_installer, cwd=str(PROJECT_ROOT))


def package_artifacts():
    """Package the compiled executable and installer into distributable release artifacts."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ["amd64", "x86_64"]:
        arch = "x64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    else:
        arch = machine

    base_name = f"networking-agent-v{VERSION}-{system}-{arch}"
    bundle_dir = RELEASE_DIR / base_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 1. Windows: Copy standalone Setup Wizard as top-level release asset
    if system == "windows":
        setup_exe_src = DIST_DIR / f"NetworkingAgent-v{VERSION}-Setup.exe"
        if not setup_exe_src.exists():
            # Fallback check
            candidates = list(DIST_DIR.glob("*Setup*.exe"))
            if candidates:
                setup_exe_src = candidates[0]

        if setup_exe_src.exists():
            setup_exe_dst = RELEASE_DIR / setup_exe_src.name
            shutil.copy2(setup_exe_src, setup_exe_dst)
            print(f"[+] Windows standalone Setup Wizard ready: {setup_exe_dst}")

    # 2. Copy binary into portable bundle directory
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
            f"title NetworkingAgent Enterprise v{VERSION}\r\n"
            '"%~dp0networking-agent.exe" %*\r\n'
            "if %ERRORLEVEL% NEQ 0 (\r\n"
            "    echo.\r\n"
            "    echo [ERROR] NetworkingAgent se cerro con codigo de salida %ERRORLEVEL%.\r\n"
            "    pause\r\n"
            ")\r\n"
        )
        (bundle_dir / "iniciar.bat").write_text(iniciar_bat, encoding="ascii")

        if (PROJECT_ROOT / "install.ps1").exists():
            shutil.copy2(PROJECT_ROOT / "install.ps1", bundle_dir / "install.ps1")
    else:
        if (PROJECT_ROOT / "install.sh").exists():
            shutil.copy2(PROJECT_ROOT / "install.sh", bundle_dir / "install.sh")

    # Create portable archive
    print(f"[*] Creating portable release archive for {system}-{arch}...")
    if system == "windows":
        archive_path = RELEASE_DIR / f"{base_name}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(bundle_dir):
                for f in files:
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(RELEASE_DIR)
                    zf.write(file_path, arcname)
        print(f"[+] Windows portable zip package ready: {archive_path}")
    else:
        archive_path = RELEASE_DIR / f"{base_name}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(bundle_dir, arcname=base_name)
        print(f"[+] Posix portable tar.gz package ready: {archive_path}")

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
