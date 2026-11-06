"""Automated unit and integration tests for NetworkingAgent Textual TUI."""

import pytest

from networking_agent.engine.observer import ConsoleAgentObserver
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.tui.app import NetworkingAgentTUIApp, TextualAgentObserver
from networking_agent.tui.modals.device_modal import DeviceModal
from networking_agent.tui.modals.hitl_modal import HitLModal
from networking_agent.tui.modals.vault_modal import VaultModal
from networking_agent.tui.widgets.audit_table import AuditTableWidget
from networking_agent.tui.widgets.banner_widget import BannerWidget
from networking_agent.tui.widgets.device_sidebar import DeviceSidebar
from networking_agent.tui.widgets.diagnostic_view import DiagnosticWorkspace
from networking_agent.tui.widgets.home_view import HomeDashboard
from networking_agent.tui.widgets.status_bar import TopStatusBar


@pytest.mark.anyio
async def test_tui_app_mounts_all_core_widgets():
    """Verify that the TUI app loads and composes its core widgets correctly."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        assert pilot.app.query_one(TopStatusBar) is not None
        assert pilot.app.query_one(DeviceSidebar) is not None
        assert pilot.app.query_one(DiagnosticWorkspace) is not None
        assert pilot.app.query_one(AuditTableWidget) is not None


@pytest.mark.anyio
async def test_tui_diagnostic_workspace_quick_chips():
    """Verify that clicking symptom quick-chips populates the textarea."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        workspace = pilot.app.query_one(DiagnosticWorkspace)
        # Click OSPF quick chip
        chip_ospf = workspace.query_one("#chip-ospf")
        chip_ospf.press()
        await pilot.pause()

        text_area = workspace.query_one("#symptom-input")
        assert "OSPF" in text_area.text

        # Click duplex quick chip
        chip_duplex = workspace.query_one("#chip-duplex")
        chip_duplex.press()
        await pilot.pause()
        assert "duplex mismatch" in text_area.text


@pytest.mark.anyio
async def test_tui_device_selection_updates_workspace():
    """Verify selecting a device in the sidebar updates the active target card."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        workspace = pilot.app.query_one(DiagnosticWorkspace)
        dev = DeviceInventory(
            host="172.16.50.1",
            device_type="cisco_nxos",
            port=22,
            username="netops",
        )
        workspace.set_device(dev)
        assert workspace.current_device is not None
        assert workspace.current_device.host == "172.16.50.1"


@pytest.mark.anyio
async def test_tui_hitl_modal_actions():
    """Test HitLModal keybindings for authorization and rejection."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        dev = DeviceInventory(host="10.10.10.1", device_type="cisco_ios")
        intent = NetworkIntent(
            diagnosis="Port in err-disabled",
            severity="HIGH",
            requires_config_change=True,
            action="restart_interface",
            target_interface="GigabitEthernet0/1",
        )

        # 1. Test authorize via 'y' key
        approved_result = []
        modal_approve = HitLModal(
            device=dev,
            intent=intent,
            candidate_cli=["default interface Gi0/1", "no shutdown"],
            rollback_info="Archive rollback",
        )
        pilot.app.push_screen(modal_approve, callback=approved_result.append)
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert approved_result == [True]

        # 2. Test reject via 'n' key
        rejected_result = []
        modal_reject = HitLModal(
            device=dev,
            intent=intent,
            candidate_cli=["shutdown"],
            rollback_info="Snapshot rollback",
        )
        pilot.app.push_screen(modal_reject, callback=rejected_result.append)
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert rejected_result == [False]


@pytest.mark.anyio
async def test_tui_observer_updates_workspace_methods():
    """Verify TextualAgentObserver methods interact properly with workspace."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        workspace = pilot.app.query_one(DiagnosticWorkspace)
        observer = TextualAgentObserver(app=pilot.app, workspace=workspace)

        # Status update
        observer.on_status_update("Running diagnostic tests...")
        await pilot.pause()

        # Diagnosis ready
        intent = NetworkIntent(
            diagnosis="MTU error on ether1",
            severity="HIGH",
            requires_config_change=True,
            action="set_interface_mtu",
            target_interface="ether1",
            mtu_value=9000,
        )
        observer.on_diagnosis_ready(intent)
        await pilot.pause()

        # No-op required
        dev = DeviceInventory(host="192.168.1.1", device_type="mikrotik_routeros")
        observer.on_no_op_required(dev, intent)
        await pilot.pause()

        # Guardrail blocked
        observer.on_guardrail_blocked(intent, "Interface ether1 is protected")
        await pilot.pause()

        # Completion
        observer.on_completion(True, "All operations completed.")
        await pilot.pause()


def test_console_observer_fallback():
    """Verify ConsoleAgentObserver is functional and conforms to the protocol."""
    observer = ConsoleAgentObserver()
    dev = DeviceInventory(host="192.168.1.1", device_type="mikrotik_routeros")
    intent = NetworkIntent(
        diagnosis="System normal",
        severity="LOW",
        requires_config_change=False,
        action="none",
    )
    observer.on_status_update("Test update")
    observer.on_diagnosis_ready(intent)
    observer.on_no_op_required(dev, intent)
    observer.on_guardrail_blocked(intent, "Blocked for test")
    observer.on_execution_progress("Step 1")
    observer.on_completion(True, "Success")


@pytest.mark.anyio
async def test_tui_device_modal_submission(tmp_path):
    """Verify DeviceModal form input and submission."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        modal = DeviceModal()
        saved_devices = []
        pilot.app.push_screen(modal, callback=saved_devices.append)
        await pilot.pause()

        # Fill inputs
        modal.query_one("#input-host").value = "10.200.1.254"
        modal.query_one("#input-username").value = "cisco"
        modal.query_one("#input-password").value = "cisco123"

        # Submit
        modal.action_save()
        await pilot.pause()
        assert len(saved_devices) == 1
        assert saved_devices[0] is not None
        assert saved_devices[0].host == "10.200.1.254"


@pytest.mark.anyio
async def test_tui_vault_modal_submission():
    """Verify VaultModal configuration updates."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        modal = VaultModal()
        settings_result = []
        pilot.app.push_screen(modal, callback=settings_result.append)
        await pilot.pause()

        modal.query_one("#input-model").value = "qwen2.5-coder:14b"
        modal.action_save()
        await pilot.pause()

        assert len(settings_result) == 1
        assert settings_result[0]["model"] == "qwen2.5-coder:14b"


@pytest.mark.anyio
async def test_tui_home_dashboard_navigation_and_banner():
    """Verify that the home dashboard renders the ASCII banner and navigates to tabs and back."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        # Home dashboard and banner must be present
        home = pilot.app.query_one(HomeDashboard)
        assert home is not None
        assert home.query_one(BannerWidget) is not None

        # Click on diagnostic card
        btn_diag = home.query_one("#btn-nav-diagnostic")
        btn_diag.press()
        await pilot.pause()

        # Active tab must now be diagnostic
        from textual.widgets import TabbedContent
        tabs = pilot.app.query_one(TabbedContent)
        assert tabs.active == "pane-diagnostic"

        # Click back button inside diagnostic view
        workspace = pilot.app.query_one(DiagnosticWorkspace)
        btn_back = workspace.query_one("#btn-back-to-home")
        btn_back.press()
        await pilot.pause()

        # Active tab must return to home
        assert tabs.active == "pane-home"


