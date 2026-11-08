"""Tests for NetworkingAgent Enterprise visual branding, logos, and icon assets."""

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
