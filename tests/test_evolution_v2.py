"""Comprehensive test suite for NetworkingAgent v2 evolution:

- Multi-protocol Configuration Intent & Brain synthesis
- Pre-flight Syntax & Guardrail Validator
- Template Engine & Batch Deployment
- TUI 5-Pillar navigation & Textual pilot interaction
"""

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import SelectionList, TabbedContent, TextArea

from networking_agent.engine.automation import BatchDeployer, TemplateEngine
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.config_intent import (
    ConfigurationIntent,
    ProtocolConfigType,
)
from networking_agent.models.device import DeviceInventory
from networking_agent.tui.app import NetworkingAgentTUIApp
from networking_agent.tui.widgets.automation_view import AutomationView
from networking_agent.tui.widgets.configuration_view import ConfigurationView
from networking_agent.tui.widgets.troubleshooting_view import TroubleshootingWorkspace

# --- 1. Syntax Validator Tests ---


def test_syntax_validator_accepts_clean_cisco_config():
    script = """
    vlan 100
     name CLIENTES
    interface GigabitEthernet0/1
     description Enlace a Distribucion
     switchport mode trunk
     switchport trunk allowed vlan 10,20,100
     no shutdown
    """
    report = ConfigSyntaxValidator.validate_script(script, vendor_family="cisco_ios")
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.line_count >= 5


def test_syntax_validator_blocks_destructive_commands():
    script = """
    interface GigabitEthernet0/1
     no shutdown
    reload
    write erase
    """
    report = ConfigSyntaxValidator.validate_script(script, vendor_family="cisco_ios")
    assert report.is_valid is False
    assert any("reinicio" in err.lower() or "reload" in err.lower() for err in report.errors)
    assert any("almacenamiento" in err.lower() or "erase" in err.lower() for err in report.errors)


def test_syntax_validator_detects_unrendered_variables():
    script = """
    interface {{ target_interface }}
     ip address {{ ip_address }} 255.255.255.0
    """
    report = ConfigSyntaxValidator.validate_script(script, vendor_family="cisco_ios")
    assert report.is_valid is False
    assert any("Variable de plantilla sin renderizar" in err for err in report.errors)


def test_syntax_validator_junos_brace_balance():
    unbalanced_junos = """
    interfaces {
        ge-0/0/0 {
            unit 0 {
                family inet {
                    address 192.168.1.1/24;
    """
    report = ConfigSyntaxValidator.validate_script(unbalanced_junos, vendor_family="juniper_junos")
    assert report.is_valid is False
    assert any("desbalanceados" in err.lower() for err in report.errors)


# --- 2. Template Engine Tests ---


def test_template_engine_renders_jinja2():
    tpl = "interface {{ iface }}\n description {{ desc }}\n no shutdown"
    rendered = TemplateEngine.render(tpl, {"iface": "GigabitEthernet0/2", "desc": "WAN_UPLINK"})
    assert "interface GigabitEthernet0/2" in rendered
    assert "description WAN_UPLINK" in rendered


def test_template_engine_builtin_templates():
    templates = TemplateEngine.get_templates()
    assert len(templates) >= 4
    assert any("Hardening" in t.name for t in templates)
    assert any("VLAN" in t.name for t in templates)
    assert any("OSPF" in t.name for t in templates)


# --- 3. Batch Deployer Tests ---


def test_batch_deployer_success_flow(tmp_path):
    mock_dev1 = DeviceInventory(host="10.0.0.1", device_type="cisco_ios", username="admin")
    mock_dev2 = DeviceInventory(host="10.0.0.2", device_type="cisco_ios", username="admin")

    clean_script = "vlan 10\n name CORP\nexit"

    mock_driver1 = MagicMock()
    mock_driver1.backup_running_config.return_value = tmp_path / "10.0.0.1_bkp.cfg"
    mock_driver1.execute_commands.return_value = "OK"

    mock_driver2 = MagicMock()
    mock_driver2.backup_running_config.return_value = tmp_path / "10.0.0.2_bkp.cfg"
    mock_driver2.execute_commands.return_value = "OK"

    with patch("networking_agent.engine.automation.get_os_driver") as mock_get_driver:
        mock_get_driver.side_effect = [mock_driver1, mock_driver2]
        deployer = BatchDeployer()
        result = deployer.deploy_to_devices([mock_dev1, mock_dev2], clean_script, vendor_family="cisco_ios")

        assert result.device_results["10.0.0.1"]["success"] is True
        assert result.device_results["10.0.0.2"]["success"] is True
        assert "2/2 exitosos" in result.summary


def test_batch_deployer_aborts_on_syntax_error():
    mock_dev = DeviceInventory(host="10.0.0.1", device_type="cisco_ios", username="admin")
    bad_script = "reload\nformat flash:"

    deployer = BatchDeployer()
    result = deployer.deploy_to_devices([mock_dev], bad_script, vendor_family="cisco_ios")

    assert result.device_results["10.0.0.1"]["success"] is False
    assert "cancelado por error sintáctico" in result.summary


# --- 4. Configuration Model Tests ---


def test_configuration_intent_model():
    intent = ConfigurationIntent(
        protocol_type=ProtocolConfigType.BGP,
        description="Configuración de Peering eBGP con ISP",
        target_host="10.10.10.1",
        candidate_commands=[
            "router bgp 65100",
            "neighbor 198.51.100.1 remote-as 65200",
            "address-family ipv4 unicast",
        ],
        verification_commands=["show ip bgp summary"],
        rollback_commands=["no router bgp 65100"],
        safety_notes="Sesión eBGP hacia ISP principal.",
    )
    assert intent.protocol_type == ProtocolConfigType.BGP
    assert len(intent.candidate_commands) == 3
    assert len(intent.verification_commands) == 1


# --- 5. TUI Full Navigation & Textual Pilot Tests ---


@pytest.mark.anyio
async def test_tui_evolution_5_pillars_navigation():
    app = NetworkingAgentTUIApp()
    async with app.run_test(size=(160, 45)) as pilot:
        tabs = app.query_one("#main-tabs", TabbedContent)
        assert tabs.active == "pane-home"

        # 1. Test clicking Card 1: Troubleshooting
        app.query_one("#btn-nav-troubleshooting").press()
        await pilot.pause()
        assert tabs.active == "pane-troubleshooting"
        assert isinstance(app.query_one("#troubleshooting-workspace"), TroubleshootingWorkspace)

        # Return Home
        app.query_one("#btn-back-to-home").press()
        await pilot.pause()
        assert tabs.active == "pane-home"

        # 2. Test clicking Card 2: Configuration
        app.query_one("#btn-nav-configuration").press()
        await pilot.pause()
        assert tabs.active == "pane-configuration"
        assert isinstance(app.query_one("#configuration-workspace"), ConfigurationView)

        # Test protocol chip in Configuration
        chip_bgp = app.query_one("#chip-proto-bgp")
        chip_bgp.press()
        await pilot.pause()
        req_box = app.query_one("#config-request-input", TextArea)
        assert "BGP" in req_box.text

        # Return Home
        app.query_one("#btn-back-from-config").press()
        await pilot.pause()
        assert tabs.active == "pane-home"

        # 3. Test clicking Card 3: Automation
        app.query_one("#btn-nav-automation").press()
        await pilot.pause()
        assert tabs.active == "pane-automation"
        auto_view = app.query_one("#automation-workspace", AutomationView)
        assert isinstance(auto_view, AutomationView)

        # Check TextArea presence and syntax validation
        editor = app.query_one("#automation-editor", TextArea)
        assert len(editor.text) > 0

        # Trigger syntax dry-run button
        app.query_one("#btn-validate-script").press()
        await pilot.pause()

        # Check selection list
        sel_list = app.query_one("#device-selection-list", SelectionList)
        assert sel_list is not None

        # Return Home via back button (TextArea captures keyboard characters)
        app.query_one("#btn-back-from-automation").press()
        await pilot.pause()
        assert tabs.active == "pane-home"

        # 4. Test Keybindings 1 to 5 from Home screen
        await pilot.press("1")
        await pilot.pause()
        assert tabs.active == "pane-troubleshooting"

        app.action_nav_tab_2()
        await pilot.pause()
        assert tabs.active == "pane-configuration"

        app.action_nav_tab_3()
        await pilot.pause()
        assert tabs.active == "pane-automation"

        app.action_nav_tab_4()
        await pilot.pause()
        assert tabs.active == "pane-inventory"

        app.action_nav_tab_5()
        await pilot.pause()
        assert tabs.active == "pane-audit"

        app.action_go_home()
        await pilot.pause()
        assert tabs.active == "pane-home"


@pytest.mark.anyio
async def test_vault_modal_dynamic_provider_selection():
    """Verify that switching AI provider dynamically changes labels, placeholders, and secret mode."""
    from textual.widgets import Input, Label, Select

    from networking_agent.tui.modals.vault_modal import VaultModal

    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        modal = VaultModal()
        pilot.app.push_screen(modal)
        await pilot.pause()

        lbl_cred = modal.query_one("#lbl-credential", Label)
        inp_cred = modal.query_one("#input-api-key", Input)
        select_provider = modal.query_one("#select-provider", Select)

        # Switch to Gemini
        select_provider.value = "gemini"
        await pilot.pause()

        assert "Gemini" in str(lbl_cred.render())
        assert inp_cred.password is True

        # Switch to Ollama
        select_provider.value = "ollama"
        await pilot.pause()

        assert "Ollama" in str(lbl_cred.render())
        assert inp_cred.password is False
        assert "http" in inp_cred.placeholder
