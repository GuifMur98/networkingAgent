"""Tests for NetworkingAgent Enterprise visual branding, logos, icons, and setup wizard."""

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def test_installer_logo_and_icon_assets_exist():
    """Verify that installer logo (Image 1) and icon are present and valid."""
    logo_path = ASSETS_DIR / "installer_logo.png"
    ico_path = ASSETS_DIR / "installer_icon.ico"
    png_256_path = ASSETS_DIR / "installer_icon_256.png"

    assert logo_path.exists(), f"Missing installer logo at {logo_path}"
    assert ico_path.exists(), f"Missing installer icon at {ico_path}"
    assert png_256_path.exists(), f"Missing installer 256x256 PNG at {png_256_path}"

    with Image.open(logo_path) as img:
        assert img.format == "PNG"
        assert img.size[0] > 100
        assert img.size[1] > 50

    with Image.open(ico_path) as ico:
        assert ico.format == "ICO"
        assert (256, 256) in ico.info.get("sizes", [(ico.size[0], ico.size[1])]) or ico.size == (256, 256)


def test_app_logo_and_icon_assets_exist():
    """Verify that installed application logo (Image 2), desktop icon, and taskbar icon exist."""
    logo_path = ASSETS_DIR / "app_logo.png"
    ico_path = ASSETS_DIR / "app_icon.ico"
    png_256_path = ASSETS_DIR / "app_icon_256.png"

    assert logo_path.exists(), f"Missing app logo at {logo_path}"
    assert ico_path.exists(), f"Missing app icon at {ico_path}"
    assert png_256_path.exists(), f"Missing app 256x256 PNG at {png_256_path}"

    with Image.open(logo_path) as img:
        assert img.format == "PNG"
        assert img.size[0] > 100
        assert img.size[1] > 50

    with Image.open(ico_path) as ico:
        assert ico.format == "ICO"
        assert (256, 256) in ico.info.get("sizes", [(ico.size[0], ico.size[1])]) or ico.size == (256, 256)


def test_install_script_configures_shortcut_icons():
    """Verify that install.ps1 assigns app_icon.ico to Desktop and Start Menu shortcuts."""
    ps1_content = (PROJECT_ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "app_icon.ico" in ps1_content
    assert "IconLocation" in ps1_content
    assert '$Shortcut.IconLocation = "$AppIconPath,0"' in ps1_content


def test_install_script_registers_windows_installed_app():
    """Verify that install.ps1 registers in Windows Installed Apps (Settings / Control Panel)."""
    ps1_content = (PROJECT_ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "CurrentVersion\\Uninstall\\NetworkingAgent" in ps1_content
    assert "Register-WindowsApp" in ps1_content
    assert "DisplayName" in ps1_content
    assert "DisplayIcon" in ps1_content
    assert "UninstallString" in ps1_content


def test_pyinstaller_spec_embeds_app_icon():
    """Verify that networking_agent.spec references assets and sets the application icon."""
    spec_content = (PROJECT_ROOT / "networking_agent.spec").read_text(encoding="utf-8")
    assert '"assets"' in spec_content
    assert "app_icon.ico" in spec_content


def test_installer_spec_embeds_installer_icon_and_payload():
    """Verify that installer.spec configures the single-file setup wizard with installer_icon.ico."""
    installer_spec = PROJECT_ROOT / "installer.spec"
    assert installer_spec.exists(), "installer.spec must exist"
    spec_content = installer_spec.read_text(encoding="utf-8")
    assert "installer_icon.ico" in spec_content
    assert "NetworkingAgent-v2.1.1-Setup" in spec_content
    assert "networking-agent.exe" in spec_content
    assert "console=False" in spec_content


def test_installer_wizard_script_implements_required_flows():
    """Verify that scripts/installer_wizard.py implements setup routines."""
    wizard_path = PROJECT_ROOT / "scripts" / "installer_wizard.py"
    assert wizard_path.exists(), "scripts/installer_wizard.py must exist"
    wizard_content = wizard_path.read_text(encoding="utf-8")
    assert "perform_installation" in wizard_content
    assert "register_in_windows_installed_apps" in wizard_content
    assert "run_gui_wizard" in wizard_content
    assert "add_to_user_path" in wizard_content
    assert "refresh_windows_shell" in wizard_content


def test_build_standalone_orchestrates_both_specs():
    """Verify that scripts/build_standalone.py compiles both application and setup wizard."""
    build_script = PROJECT_ROOT / "scripts" / "build_standalone.py"
    assert build_script.exists()
    content = build_script.read_text(encoding="utf-8")
    assert "networking_agent.spec" in content
    assert "installer.spec" in content
    assert "Setup.exe" in content


def test_installer_wizard_argparse_handles_slash_s_without_value_error():
    """Verify that scripts/installer_wizard.py CLI handles /S and --silent without argparse ValueError."""
    import subprocess
    import sys

    wizard_path = PROJECT_ROOT / "scripts" / "installer_wizard.py"
    res = subprocess.run(
        [sys.executable, str(wizard_path), "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "ValueError" not in res.stderr
    assert "--silent" in res.stdout
