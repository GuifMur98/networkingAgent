"""Comprehensive unit and integration tests for Module 3 (Automation Suite).

Tests cover:
- Persistent template storage & parameter variable schema
- Advanced OS syntax checking across Cisco IOS, Cisco NX-OS, Junos, and RouterOS v7
- Batch deployer progress telemetry
- Automation workspace TUI interactions
"""

from unittest.mock import MagicMock, patch

import pytest

from networking_agent.core.db import db
from networking_agent.engine.automation import BatchDeployer, TemplateEngine
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.device import DeviceInventory
from networking_agent.tui.app import NetworkingAgentTUIApp
from networking_agent.tui.widgets.automation_view import AutomationView


# =========================================================================
# 1. Template Storage & Jinja2 Variable Parsing Tests
# =========================================================================
def test_template_variable_extraction():
    content = """
    interface {{ target_interface }}
     description {{ description_text }}
     ip address {{ ip_address }} {{ subnet_mask }}
     vlan {{ vlan_id }}
    """
    vars_found = TemplateEngine.extract_variables(content)
    assert vars_found == ["description_text", "ip_address", "subnet_mask", "target_interface", "vlan_id"]


def test_template_database_persistence_and_protection():
    test_name = "TEST_CUSTOM_BGP_TEMPLATE"
    # Clean up if existed
    TemplateEngine.delete_custom_template(test_name)

    # Save custom template
    tpl = TemplateEngine.save_custom_template(
        name=test_name,
        vendor_family="cisco_ios",
        description="Plantilla de prueba para BGP",
        template_content="router bgp {{ as_num }}\n neighbor {{ peer_ip }} remote-as {{ peer_as }}",
        parameters_schema={"as_num": "65001", "peer_ip": "10.0.0.2", "peer_as": "65002"},
    )
    assert tpl.name == test_name
    assert "as_num" in tpl.parameters_schema

    # Retrieve from DB
    loaded = db.get_template_by_name(test_name)
    assert loaded is not None
    assert loaded["vendor_family"] == "cisco_ios"
    assert loaded["is_builtin"] == 0

    # Render template
    rendered = TemplateEngine.render(
        tpl.template_content,
        {"as_num": "65100", "peer_ip": "192.168.1.2", "peer_as": "65200"},
    )
    assert "router bgp 65100" in rendered
    assert "neighbor 192.168.1.2 remote-as 65200" in rendered

    # Delete custom template
    deleted = TemplateEngine.delete_custom_template(test_name)
    assert deleted is True

    # Attempt to delete a builtin template must be refused
    builtin_deleted = TemplateEngine.delete_custom_template("Cisco IOS: Hardening Base y Seguridad")
    assert builtin_deleted is False


# =========================================================================
# 2. Advanced Multi-Vendor OS Syntax Validation Tests
# =========================================================================
def test_syntax_validator_cisco_ios_vlan_out_of_range():
    bad_vlan = "vlan 5000\n name INVALID"
    report = ConfigSyntaxValidator.validate_script(bad_vlan, vendor_family="cisco_ios")
    assert report.is_valid is False
    assert any("5000" in err and "rango" in err.lower() for err in report.errors)


def test_syntax_validator_cisco_ios_wildcard_and_cidr_warnings():
    script = """
    interface GigabitEthernet0/1
     ip address 192.168.1.1/24
    router ospf 1
     network 10.0.0.0 255.255.255.0 area 0
    """
    report = ConfigSyntaxValidator.validate_script(script, vendor_family="cisco_ios")
    assert report.is_valid is True  # Warnings do not block execution unless fatal
    assert any("máscara wildcard" in w.lower() for w in report.warnings)
    assert any("cidr" in w.lower() or "decimal" in w.lower() for w in report.warnings)


def test_syntax_validator_nxos_missing_feature_advisory():
    nxos_script = """
    router ospf 10
     router-id 1.1.1.1
    """
    report = ConfigSyntaxValidator.validate_script(nxos_script, vendor_family="cisco_nxos")
    assert any("feature ospf" in w.lower() for w in report.warnings)

    # With feature included
    nxos_valid = """
    feature ospf
    router ospf 10
     router-id 1.1.1.1
    """
    report_valid = ConfigSyntaxValidator.validate_script(nxos_valid, vendor_family="cisco_nxos")
    assert not any("feature ospf" in w.lower() for w in report_valid.warnings)


def test_syntax_validator_junos_rejects_decimal_mask():
    bad_junos = "set interfaces ge-0/0/0 unit 0 family inet address 192.168.1.1 255.255.255.0"
    report = ConfigSyntaxValidator.validate_script(bad_junos, vendor_family="juniper_junos")
    assert report.is_valid is False
    assert any("cidr" in err.lower() for err in report.errors)


def test_syntax_validator_junos_rejects_cisco_syntax():
    cisco_in_junos = """
    interface GigabitEthernet0/1
     no shutdown
    """
    report = ConfigSyntaxValidator.validate_script(cisco_in_junos, vendor_family="juniper_junos")
    assert report.is_valid is False
    assert any("cisco" in err.lower() for err in report.errors)


def test_syntax_validator_routeros_prefix_and_spaced_equals():
    bad_routeros = "ip address add address = 10.0.0.1/24 interface=ether1"
    report = ConfigSyntaxValidator.validate_script(bad_routeros, vendor_family="mikrotik_routeros")
    # Must start with '/' or ':'
    assert report.is_valid is False
    assert any("iniciar con '/'" in err for err in report.errors)

    # Valid prefix but spaced equal
    spaced_ro = "/ip address add address = 10.0.0.1/24 interface=ether1"
    report_spaced = ConfigSyntaxValidator.validate_script(spaced_ro, vendor_family="mikrotik_routeros")
    assert any("espacios" in w.lower() for w in report_spaced.warnings)


def test_syntax_validator_routeros_v6_v7_advisory():
    v6_script = "/routing ospf network add network=10.0.0.0/24 area=backbone"
    report = ConfigSyntaxValidator.validate_script(v6_script, vendor_family="mikrotik_routeros")
    assert any("routeros v6->v7" in w.lower() for w in report.warnings)


# =========================================================================
# 3. Batch Deployer Progress & Execution Telemetry Tests
# =========================================================================
def test_batch_deployer_notifies_progress():
    mock_observer = MagicMock()
    mock_dev = DeviceInventory(host="192.168.1.50", device_type="cisco_ios", username="admin")

    clean_script = """
    vlan 200
     name TEST_PROGRESS
    exit
    """

    with patch("networking_agent.engine.automation.get_os_driver") as mock_get_driver:
        mock_driver = MagicMock()
        mock_driver.backup_running_config.return_value = MagicMock(name="snapshot.cfg")
        mock_driver.execute_commands.return_value = "Applied successfully"
        mock_get_driver.return_value = mock_driver

        deployer = BatchDeployer(observer=mock_observer)
        result = deployer.deploy_to_devices([mock_dev], clean_script, vendor_family="cisco_ios")

        assert result.device_results["192.168.1.50"]["success"] is True
        assert mock_observer.update_progress.call_count >= 3
        # Check final progress call was 100%
        last_progress_args = mock_observer.update_progress.call_args[0]
        assert last_progress_args[0] == 100.0


# =========================================================================
# 4. TUI Automation Workspace Interaction Tests
# =========================================================================
@pytest.mark.anyio
async def test_tui_automation_workspace_interactions():
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Switch to tab 3 (Automation)
        app.action_nav_tab_3()
        await pilot.pause()

        auto_view = app.query_one("#automation-workspace", AutomationView)
        assert auto_view is not None

        # Check that progress bar and labels exist
        pbar = auto_view.query_one("#auto-progress-bar")
        assert pbar is not None

        # Test selecting all and deselecting all devices
        btn_select_all = auto_view.query_one("#btn-select-all-devices")
        btn_select_all.press()
        await pilot.pause()

        btn_deselect_all = auto_view.query_one("#btn-deselect-all-devices")
        btn_deselect_all.press()
        await pilot.pause()

        # Test progress update thread-safety
        auto_view.update_progress(50.0, "Paso de prueba en ejecución")
        await pilot.pause()
        lbl_step = auto_view.query_one("#lbl-auto-step")
        assert "prueba" in str(lbl_step.render())


@pytest.mark.anyio
async def test_tui_template_modal_workflow():
    from networking_agent.tui.modals.template_modal import TemplateModal

    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        modal = TemplateModal(initial_content="vlan {{ vlan_id }}\n name {{ vlan_name }}")
        app.push_screen(modal)
        await pilot.pause()

        # Check modal controls
        name_input = modal.query_one("#input-tpl-name")
        name_input.value = "TEST_MODAL_VLAN"

        # Press auto-detect variables
        btn_detect = modal.query_one("#btn-detect-vars")
        btn_detect.press()
        await pilot.pause()

        feedback = modal.query_one("#lbl-tpl-feedback")
        assert "vlan_id" in str(feedback.render())

        # Press Save
        btn_save = modal.query_one("#btn-save-tpl")
        btn_save.press()
        await pilot.pause()

        # Check that template was stored
        saved = db.get_template_by_name("TEST_MODAL_VLAN")
        assert saved is not None
        # Clean up
        TemplateEngine.delete_custom_template("TEST_MODAL_VLAN")
