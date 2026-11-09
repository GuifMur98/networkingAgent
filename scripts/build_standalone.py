#!/usr/bin/env python3
"""Build script for compiling NetworkingAgent Enterprise into standalone binaries and installers."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "release-artifacts"
VERSION = "2.2.0"


def check_prerequisites():
    """Ensure PyInstaller, Pillow, and pefile are installed."""
    try:
        import PyInstaller

        print(f"[*] Found PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller is not installed. Installing via uv / pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.11.0"])

    try:
        import PIL

        print(f"[*] Found Pillow version: {PIL.__version__}")
    except ImportError:
        print("[!] Pillow is not installed. Installing via uv / pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow>=10.0.0"])

    if platform.system().lower() == "windows":
        try:
            import pefile

            print(f"[*] Found pefile version: {pefile.__version__}")
        except ImportError:
            print("[*] Installing pefile for Windows PE resource verification...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile>=2023.2.7"])


def clean_previous_builds():
    """Remove artifacts from previous builds."""
    print("[*] Cleaning previous build directories...")
    for d in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def verify_exe_icon(exe_path: Path, label: str = "Executable") -> bool:
    """Verify that the compiled Windows PE executable contains RT_ICON and RT_GROUP_ICON."""
    try:
        import pefile

        pe = pefile.PE(str(exe_path))
        has_icon = False
        has_group = False
        if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                if entry.id == pefile.RESOURCE_TYPE["RT_ICON"]:
                    has_icon = True
                if entry.id == pefile.RESOURCE_TYPE["RT_GROUP_ICON"]:
                    has_group = True
        pe.close()

        if has_icon and has_group:
            print(f"[+] Verified PE icon resources in {label} ({exe_path.name}): RT_ICON=OK, RT_GROUP_ICON=OK")
            return True
        else:
            print(f"[!] Warning: {label} ({exe_path.name}) icon verification: RT_ICON={has_icon}, RT_GROUP={has_group}")
            return False
    except Exception as e:
        print(f"[!] Note: Could not verify PE icon with pefile: {e}")
        return True


def build_binary():
    """Invoke PyInstaller using the project spec files."""
    system = platform.system().lower()
    spec_path = PROJECT_ROOT / "networking_agent.spec"
    app_icon = PROJECT_ROOT / "assets" / "app_icon.ico"
    if system == "windows":
        assert app_icon.exists(), f"Missing required application icon at {app_icon}"

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

    # Verify app binary icon on Windows
    if system == "windows":
        app_exe = DIST_DIR / "networking-agent.exe"
        if app_exe.exists():
            verify_exe_icon(app_exe, label="Application Binary")

    # On Windows, compile the single-file GUI Setup Wizard installer
    if system == "windows":
        installer_spec = PROJECT_ROOT / "installer.spec"
        installer_icon = PROJECT_ROOT / "assets" / "installer_icon.ico"
        assert installer_icon.exists(), f"Missing required installer icon at {installer_icon}"

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

        setup_exe = DIST_DIR / f"NetworkingAgent-v{VERSION}-Setup.exe"
        if setup_exe.exists():
            verify_exe_icon(setup_exe, label="Setup Wizard Installer")


def package_artifacts():
    """Package the release artifacts.

    On Windows: Generates ONLY the single-file Setup Wizard (NetworkingAgent-vX.Y.Z-Setup.exe).
    No loose batch scripts, no extra zip files.
    On Posix (Linux/macOS): Generates the standalone tar.gz bundle.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ["amd64", "x86_64"]:
        arch = "x64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    else:
        arch = machine

    # 1. Windows: Copy ONLY the standalone Setup Wizard into release-artifacts
    if system == "windows":
        setup_exe_src = DIST_DIR / f"NetworkingAgent-v{VERSION}-Setup.exe"
        if not setup_exe_src.exists():
            candidates = list(DIST_DIR.glob("*Setup*.exe"))
            if candidates:
                setup_exe_src = candidates[0]

        if not setup_exe_src.exists():
            raise FileNotFoundError(f"Setup Wizard executable not found in {DIST_DIR}")

        verify_exe_icon(setup_exe_src, label="Final Setup Wizard Artifact")

        setup_exe_dst = RELEASE_DIR / setup_exe_src.name
        shutil.copy2(setup_exe_src, setup_exe_dst)
        size_mb = setup_exe_dst.stat().st_size / (1024 * 1024)
        print(f"[+] Windows enterprise Setup Wizard ready: {setup_exe_dst} ({size_mb:.1f} MB)")
        return setup_exe_dst

    # 2. Posix (Linux / macOS): Create portable tar.gz
    base_name = f"networking-agent-v{VERSION}-{system}-{arch}"
    bundle_dir = RELEASE_DIR / base_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    binary_src = DIST_DIR / "networking-agent"
    binary_dst = bundle_dir / "networking-agent"
    if not binary_src.exists():
        raise FileNotFoundError(f"Compiled binary not found at: {binary_src}")

    shutil.copy2(binary_src, binary_dst)
    os.chmod(binary_dst, 0o755)

    for doc in ["README.md", "LICENSE"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, bundle_dir / doc)

    if (PROJECT_ROOT / "install.sh").exists():
        shutil.copy2(PROJECT_ROOT / "install.sh", bundle_dir / "install.sh")

    print(f"[*] Creating portable release archive for {system}-{arch}...")
    archive_path = RELEASE_DIR / f"{base_name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tf:
        tf.add(bundle_dir, arcname=base_name)
    shutil.rmtree(bundle_dir, ignore_errors=True)
    print(f"[+] Posix portable tar.gz package ready: {archive_path}")
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
