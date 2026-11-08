"""Main reactive Textual TUI application for NetworkingAgent."""

import threading
from typing import Any, List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import CommandPalette
from textual.containers import Horizontal
from textual.widgets import Footer, Log, TabbedContent, TabPane

from networking_agent.core.config import settings
from networking_agent.core.crypto import vault
from networking_agent.core.db import db
from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.engine.automation import BatchDeployer
from networking_agent.engine.observer import AgentObserver
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.models.telemetry import TelemetryEvent
from networking_agent.tui.commands import NetworkAgentCommandProvider
from networking_agent.tui.modals.device_modal import DeviceModal
from networking_agent.tui.modals.hitl_modal import HitLModal
from networking_agent.tui.modals.vault_modal import VaultModal
from networking_agent.tui.widgets.audit_table import AuditTableWidget
from networking_agent.tui.widgets.automation_view import AutomationView
from networking_agent.tui.widgets.configuration_view import ConfigurationView
from networking_agent.tui.widgets.device_inventory_view import DeviceInventoryView
from networking_agent.tui.widgets.device_sidebar import DeviceSidebar
from networking_agent.tui.widgets.home_view import HomeDashboard
from networking_agent.tui.widgets.status_bar import TopStatusBar
from networking_agent.tui.widgets.troubleshooting_view import TroubleshootingWorkspace


class TextualAgentObserver(AgentObserver):
    """Bridge observer connecting NetworkAssistantAgent events to Textual widgets."""

    def __init__(self, app: "NetworkingAgentTUIApp", workspace: Optional[Any] = None):
        self.app = app
        self.workspace = workspace

    def _safe_call(self, callback, *args, **kwargs) -> None:
        """Call a UI method safely regardless of whether we are in main loop or worker thread."""
        if getattr(self.app, "_thread_id", None) == threading.get_ident():
            callback(*args, **kwargs)
        else:
            self.app.call_from_thread(callback, *args, **kwargs)

    def on_status_update(self, message: str) -> None:
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(self.workspace.append_log, f"[*] {message}")

    def on_diagnosis_ready(self, intent: NetworkIntent) -> None:
        if self.workspace and hasattr(self.workspace, "display_diagnosis"):
            self._safe_call(self.workspace.display_diagnosis, intent)
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(
                self.workspace.append_log,
                f"[bold cyan]AI Diagnosis:[/] {intent.diagnosis} (Severity: {intent.severity})",
            )

    def on_no_op_required(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        if self.workspace and hasattr(self.workspace, "display_no_op"):
            self._safe_call(self.workspace.display_no_op, device, intent)
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(
                self.workspace.append_log,
                "[bold green][OK] Evaluacion diagnostica finalizada: No se requieren cambios en la configuracion.[/]",
            )

    def on_guardrail_blocked(self, intent: NetworkIntent, reason: str) -> None:
        if self.workspace and hasattr(self.workspace, "display_guardrail_block"):
            self._safe_call(self.workspace.display_guardrail_block, intent, reason)
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(
                self.workspace.append_log,
                f"[bold red][ALERTA] Guardarail activado: {reason}[/]",
            )

    def on_hitl_approval_required(
        self,
        device: DeviceInventory,
        intent: NetworkIntent,
        candidate_cli: List[str],
        rollback_info: str,
    ) -> bool:
        """Pushes HitLModal on the UI thread and blocks only the worker thread until decision."""
        decision_event = threading.Event()
        approval_result = [False]

        def show_modal():
            def on_modal_result(approved: bool) -> None:
                approval_result[0] = bool(approved)
                decision_event.set()

            self.app.push_screen(
                HitLModal(
                    device=device,
                    intent=intent,
                    candidate_cli=candidate_cli,
                    rollback_info=rollback_info,
                ),
                callback=on_modal_result,
            )

        self._safe_call(show_modal)
        # Block only the worker thread; main event loop stays 100% active
        decision_event.wait()
        return approval_result[0]

    def on_execution_progress(self, step: str) -> None:
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(self.workspace.append_log, step)

    def on_progress(self, percentage: int, step: str) -> None:
        if self.workspace and hasattr(self.workspace, "update_progress"):
            self._safe_call(self.workspace.update_progress, percentage, step)

    def on_completion(self, success: bool, message: str) -> None:
        color = "bold green" if success else "bold red"
        if self.workspace and hasattr(self.workspace, "append_log"):
            self._safe_call(self.workspace.append_log, f"[{color}]{message}[/{color}]")


class NetworkingAgentTUIApp(App):
    """Main terminal user interface application for NetworkingAgent."""

    TITLE = "NetworkingAgent Enterprise AI"
    SUB_TITLE = "Autonomous & Closed-Loop Network Assistant"
    CSS_PATH = "styles.tcss"
    COMMANDS = {NetworkAgentCommandProvider}

    BINDINGS = [
        Binding("h", "go_home", "Inicio", show=True),
        Binding("escape", "escape_or_home", "Inicio", show=False),
        Binding("ctrl+h", "go_home", "Inicio", show=False),
        Binding("q", "quit", "Salir", show=True),
        Binding("d", "add_device", "Nuevo Equipo", show=True),
        Binding("s", "open_settings", "Ajustes IA", show=True),
        Binding("r", "refresh_all", "Recargar", show=True),
        Binding("ctrl+p", "command_palette", "Paleta", show=False),
        Binding("f5", "refresh_all", "Recargar", show=False),
        Binding("ctrl+r", "refresh_all", "Recargar", show=False),
        Binding("1", "nav_tab_1", "Troubleshooting", show=False),
        Binding("2", "nav_tab_2", "Configuración", show=False),
        Binding("3", "nav_tab_3", "Automatización", show=False),
        Binding("4", "nav_tab_4", "Inventario", show=False),
        Binding("5", "nav_tab_5", "Auditoría", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_busy = False

    def compose(self) -> ComposeResult:
        ai_provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
        ai_model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:7b"
        auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve
        devices = db.list_devices()

        yield TopStatusBar(
            brain_info=f"{ai_provider}:{ai_model}",
            device_count=len(devices),
            auto_approve=auto_approve,
            id="top-bar",
        )

        with TabbedContent(id="main-tabs", initial="pane-home"):
            with TabPane("Inicio", id="pane-home"):
                yield HomeDashboard(id="home-widget")

            with TabPane("Troubleshooting", id="pane-troubleshooting"):
                with Horizontal(id="main-split"):
                    yield DeviceSidebar(id="device-sidebar")
                    yield TroubleshootingWorkspace(id="troubleshooting-workspace")

            with TabPane("Configuracion", id="pane-configuration"):
                with Horizontal(id="config-split"):
                    yield DeviceSidebar(id="device-sidebar-config")
                    yield ConfigurationView(id="configuration-workspace")

            with TabPane("Automatizacion", id="pane-automation"):
                yield AutomationView(id="automation-workspace")

            with TabPane("Inventario", id="pane-inventory"):
                yield DeviceInventoryView(id="inventory-widget")

            with TabPane("Auditoria", id="pane-audit"):
                yield AuditTableWidget(id="audit-widget")

        yield Footer(show_command_palette=True)

    def on_mount(self) -> None:
        """Trigger initial device sync across sidebars and views."""
        first_dev = None
        for sidebar in self.query(DeviceSidebar):
            sidebar.reload_devices()
            if not first_dev and sidebar.devices:
                first_dev = sidebar.devices[0]

        if first_dev:
            try:
                self.query_one("#troubleshooting-workspace", TroubleshootingWorkspace).set_device(first_dev)
            except Exception:
                pass
            try:
                self.query_one("#configuration-workspace", ConfigurationView).set_device(first_dev)
            except Exception:
                pass

        self._prewarm_ai_cache()

    @work(thread=True)
    def _prewarm_ai_cache(self) -> None:
        """Silently pre-warm local Ollama models cache in background thread so opening modal is instantaneous."""
        try:
            from networking_agent.brains.discovery import get_installed_ollama_models

            get_installed_ollama_models(force_refresh=True)
        except Exception:
            pass

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Dynamic actions filter: on Home show all shortcuts; on modules show ONLY 'h' Inicio."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            is_home = tabs.active == "pane-home"
        except Exception:
            is_home = True

        if is_home:
            return True
        else:
            return action in ["go_home", "escape_or_home"]

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Refresh active bindings in footer whenever active tab changes."""
        self.screen.refresh_bindings()

    def action_go_home(self) -> None:
        """Switch navigation back to the Home Dashboard."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-home"
        try:
            home = self.query_one(HomeDashboard)
            home.update_status_card()
            self.query_one("#btn-nav-troubleshooting").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def action_escape_or_home(self) -> None:
        """Handle escape: unfocus active input/editor to back button, or return to Home."""
        from textual.widgets import Input, TextArea

        if self.focused and isinstance(self.focused, (TextArea, Input)):
            tabs = self.query_one("#main-tabs", TabbedContent)
            active = tabs.active
            btn_map = {
                "pane-troubleshooting": "#btn-back-to-home",
                "pane-configuration": "#btn-back-from-config",
                "pane-automation": "#btn-back-from-automation",
                "pane-inventory": "#btn-back-from-inventory",
                "pane-audit": "#btn-back-from-audit",
            }
            if active in btn_map:
                try:
                    self.query_one(btn_map[active]).focus()
                    return
                except Exception:
                    pass
            self.set_focus(None)
        else:
            self.action_go_home()

    def action_nav_tab_1(self) -> None:
        """Switch navigation to Troubleshooting workspace."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-troubleshooting"
        try:
            self.query_one("#btn-back-to-home").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def action_nav_tab_2(self) -> None:
        """Switch navigation to Configuration view."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-configuration"
        try:
            self.query_one("#btn-back-from-config").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def action_nav_tab_3(self) -> None:
        """Switch navigation to Automation view."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-automation"
        try:
            self.query_one("#btn-back-from-automation").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def action_nav_tab_4(self) -> None:
        """Switch navigation to Device Inventory view."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-inventory"
        try:
            self.query_one("#btn-back-from-inventory").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def action_nav_tab_5(self) -> None:
        """Switch navigation to Audit trail view."""
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "pane-audit"
        try:
            self.query_one("#btn-back-from-audit").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def on_home_dashboard_navigate_to_tab(self, event: HomeDashboard.NavigateToTab) -> None:
        self.set_focus(None)
        tabs = self.query_one("#main-tabs", TabbedContent)
        # Handle alias
        target_tab = (
            "pane-troubleshooting" if event.tab_id in ["pane-diagnostic", "pane-troubleshooting"] else event.tab_id
        )
        tabs.active = target_tab
        try:
            if target_tab == "pane-troubleshooting":
                self.query_one("#btn-back-to-home").focus()
            elif target_tab == "pane-configuration":
                self.query_one("#btn-back-from-config").focus()
            elif target_tab == "pane-automation":
                self.query_one("#btn-back-from-automation").focus()
            elif target_tab == "pane-inventory":
                self.query_one("#btn-back-from-inventory").focus()
            elif target_tab == "pane-audit":
                self.query_one("#btn-back-from-audit").focus()
        except Exception:
            pass
        self.screen.refresh_bindings()

    def on_home_dashboard_open_settings_requested(self, event: HomeDashboard.OpenSettingsRequested) -> None:
        self.action_open_settings()

    def on_troubleshooting_workspace_return_home_requested(
        self, event: TroubleshootingWorkspace.ReturnHomeRequested
    ) -> None:
        self.action_go_home()

    def on_configuration_view_return_home_requested(self, event: ConfigurationView.ReturnHomeRequested) -> None:
        self.action_go_home()

    def on_automation_view_return_home_requested(self, event: AutomationView.ReturnHomeRequested) -> None:
        self.action_go_home()

    def on_device_inventory_view_return_home_requested(self, event: DeviceInventoryView.ReturnHomeRequested) -> None:
        self.action_go_home()

    def on_device_inventory_view_add_device_requested(self, event: DeviceInventoryView.AddDeviceRequested) -> None:
        self.action_add_device()

    def on_device_inventory_view_device_deleted(self, event: DeviceInventoryView.DeviceDeleted) -> None:
        for sidebar in self.query(DeviceSidebar):
            sidebar.reload_devices()
        try:
            auto_view = self.query_one(AutomationView)
            auto_view.reload_devices()
        except Exception:
            pass
        status_bar = self.query_one(TopStatusBar)
        status_bar.update_device_count(len(db.list_devices()))

    def on_audit_table_widget_return_home_requested(self, event: AuditTableWidget.ReturnHomeRequested) -> None:
        self.action_go_home()

    def on_device_sidebar_device_selected(self, event: DeviceSidebar.DeviceSelected) -> None:
        """Route selected device to relevant workspaces."""
        try:
            tb_workspace = self.query_one("#troubleshooting-workspace", TroubleshootingWorkspace)
            tb_workspace.set_device(event.device)
        except Exception:
            pass
        try:
            cfg_workspace = self.query_one("#configuration-workspace", ConfigurationView)
            cfg_workspace.set_device(event.device)
        except Exception:
            pass

    def on_device_sidebar_add_device_requested(self, event: DeviceSidebar.AddDeviceRequested) -> None:
        self.action_add_device()

    def action_add_device(self) -> None:
        """Display DeviceModal to register a new host."""

        def on_device_added(device: Optional[DeviceInventory]) -> None:
            if device:
                for sidebar in self.query(DeviceSidebar):
                    sidebar.reload_devices()
                try:
                    inv_view = self.query_one(DeviceInventoryView)
                    inv_view.reload_devices()
                except Exception:
                    pass
                try:
                    auto_view = self.query_one(AutomationView)
                    auto_view.reload_devices()
                except Exception:
                    pass
                status_bar = self.query_one(TopStatusBar)
                status_bar.update_device_count(len(db.list_devices()))

        self.push_screen(DeviceModal(), callback=on_device_added)

    def action_open_settings(self) -> None:
        """Display VaultModal to configure AI models and keys."""

        def on_settings_saved(result: Optional[dict]) -> None:
            if result:
                status_bar = self.query_one(TopStatusBar)
                status_bar.update_brain(f"{result['provider']}:{result['model']}")
                status_bar.update_hitl_mode(result.get("auto_approve") == "true")
                try:
                    home = self.query_one(HomeDashboard)
                    home.update_status_card()
                except Exception:
                    pass

        self.push_screen(VaultModal(), callback=on_settings_saved)

    def action_refresh_all(self) -> None:
        """Reload inventory, devices, and audit log across all active views."""
        dev_count = 0
        try:
            devices = db.list_devices()
            dev_count = len(devices)
        except Exception:
            devices = []

        # 1. Reload all sidebars
        for sidebar in self.query(DeviceSidebar):
            sidebar.reload_devices()

        # 2. Reload Inventory View
        try:
            inv_view = self.query_one(DeviceInventoryView)
            inv_view.reload_devices()
        except Exception:
            pass

        # 3. Reload Automation View
        try:
            auto_view = self.query_one(AutomationView)
            auto_view.reload_devices()
            auto_view.reload_templates()
        except Exception:
            pass

        # 4. Reload Audit Table
        try:
            audit_widget = self.query_one(AuditTableWidget)
            audit_widget.reload_audit_data()
        except Exception:
            pass

        # 5. Reload Home Dashboard
        try:
            home_view = self.query_one(HomeDashboard)
            home_view.reload_dashboard()
        except Exception:
            pass

        # 6. Update Top Status Bar
        try:
            status_bar = self.query_one(TopStatusBar)
            status_bar.update_device_count(dev_count)
        except Exception:
            pass

        # 7. Surface visual confirmation notification
        self.notify(
            f"Sincronización completa: {dev_count} equipos y bitácora actualizados.",
            title="SISTEMA RECARGADO",
            severity="information",
            timeout=2.5,
        )

    def action_command_palette(self) -> None:
        """Show the Command Palette with customized placeholder and without emojis."""
        if self.use_command_palette and not CommandPalette.is_open(self):
            self.push_screen(
                CommandPalette(
                    id="--command-palette",
                    placeholder="Escriba un comando o búsqueda (ej: ping, equipos, hitl, auditoria)...",
                )
            )

    def action_test_connectivity(self) -> None:
        """Switch to inventory view and execute full reachability test (Ping + SSH)."""
        self.action_nav_tab_4()
        try:
            inv = self.query_one(DeviceInventoryView)
            self.set_timer(0.1, inv.action_test_full_connectivity)
        except Exception:
            pass

    def action_ping_device(self) -> None:
        """Switch to inventory view and execute ICMP ping probe."""
        self.action_nav_tab_4()
        try:
            inv = self.query_one(DeviceInventoryView)
            self.set_timer(0.1, inv.action_ping_device)
        except Exception:
            pass

    def action_test_ssh_port(self) -> None:
        """Switch to inventory view and execute TCP port 22 SSH connection test."""
        self.action_nav_tab_4()
        try:
            inv = self.query_one(DeviceInventoryView)
            self.set_timer(0.1, inv.action_test_connection)
        except Exception:
            pass

    def action_new_template(self) -> None:
        """Switch to automation view and open new Jinja2 template modal."""
        self.action_nav_tab_3()
        try:
            auto_view = self.query_one(AutomationView)
            self.set_timer(0.1, auto_view._open_new_template_modal)
        except Exception:
            pass

    def action_validate_automation_script(self) -> None:
        """Switch to automation view and run dry-run syntax validation."""
        self.action_nav_tab_3()
        try:
            auto_view = self.query_one(AutomationView)
            self.set_timer(0.1, auto_view._run_syntax_validation)
        except Exception:
            pass

    def action_select_all_automation_devices(self) -> None:
        """Switch to automation view and select all devices for batch deployment."""
        self.action_nav_tab_3()
        try:
            auto_view = self.query_one(AutomationView)
            self.set_timer(0.1, lambda: auto_view._set_all_devices_selection(True))
        except Exception:
            pass

    def action_deselect_all_automation_devices(self) -> None:
        """Switch to automation view and deselect all devices in batch list."""
        self.action_nav_tab_3()
        try:
            auto_view = self.query_one(AutomationView)
            self.set_timer(0.1, lambda: auto_view._set_all_devices_selection(False))
        except Exception:
            pass

    def action_toggle_hitl(self) -> None:
        """Toggle Human-in-the-Loop vs Auto-Approve execution mode."""
        current = db.get_setting("auto_approve") == "true" or settings.auto_approve
        new_val = not current
        db.set_setting("auto_approve", "true" if new_val else "false")
        try:
            status_bar = self.query_one(TopStatusBar)
            status_bar.update_hitl_mode(new_val)
        except Exception:
            pass
        try:
            home = self.query_one(HomeDashboard)
            home.update_status_card()
        except Exception:
            pass
        mode_str = "AUTO-APROBACION DIRECTA (HITL Desactivado)" if new_val else "HITL ACTIVO (Supervision Humana)"
        sev = "warning" if new_val else "information"
        self.notify(f"Modo de operacion cambiado a: {mode_str}", title="GUARDARRAILES", severity=sev, timeout=3.0)

    def action_export_audit(self) -> None:
        """Switch to audit view and trigger export to JSON."""
        self.action_nav_tab_5()
        try:
            audit = self.query_one(AuditTableWidget)
            self.set_timer(0.1, audit.export_audit_to_json)
        except Exception:
            pass

    def action_purge_audit_tests(self) -> None:
        """Switch to audit view and purge synthetic automated test records."""
        self.action_nav_tab_5()
        try:
            audit = self.query_one(AuditTableWidget)
            self.set_timer(0.1, audit.purge_test_records)
        except Exception:
            pass

    def action_clear_active_console(self) -> None:
        """Clear logs and terminal outputs in active workspaces."""
        cleared = False
        for selector in ["#log-terminal", "#config-log-terminal", "#automation-log-terminal"]:
            try:
                log_widget = self.query_one(selector, Log)
                log_widget.clear()
                cleared = True
            except Exception:
                pass
        if cleared:
            self.notify(
                "Terminal de salida y bitacora de pantalla limpiadas.",
                title="CONSOLA LIMPIA",
                severity="information",
            )

    def action_load_symptom_bgp(self) -> None:
        """Switch to troubleshooting and load BGP symptom preset."""
        self.action_nav_tab_1()
        try:
            tb = self.query_one(TroubleshootingWorkspace)
            tb._fill_symptom("El vecino BGP 10.0.0.2 no establece sesion y permanece en estado Idle / Active.")
        except Exception:
            pass

    def action_load_symptom_ospf(self) -> None:
        """Switch to troubleshooting and load OSPF symptom preset."""
        self.action_nav_tab_1()
        try:
            tb = self.query_one(TroubleshootingWorkspace)
            tb._fill_symptom("Adyacencia OSPF en Gi0/1 estancada en estado EXSTART/EXCHANGE.")
        except Exception:
            pass

    def action_load_symptom_packetloss(self) -> None:
        """Switch to troubleshooting and load packet loss symptom preset."""
        self.action_nav_tab_1()
        try:
            tb = self.query_one(TroubleshootingWorkspace)
            tb._fill_symptom("Perdida recurrente de paquetes y errores CRC reportados en el enlace Gi0/1.")
        except Exception:
            pass

    def action_load_symptom_vlan(self) -> None:
        """Switch to troubleshooting and load VLAN symptom preset."""
        self.action_nav_tab_1()
        try:
            tb = self.query_one(TroubleshootingWorkspace)
            tb._fill_symptom("El trafico entre switches de la VLAN 100 no cruza el enlace troncal Gi0/2.")
        except Exception:
            pass

    def action_show_shortcuts(self) -> None:
        """Display quick keyboard shortcuts reference."""
        self.notify(
            "Atajos principales:\n"
            "h: Inicio | 1..5: Modulos | d: Nuevo Equipo | s: Ajustes IA | r/F5: Recargar\n"
            "^p: Paleta de Comandos | q: Salir",
            title="ATAJOS DE TECLADO // GUIA RAPIDA",
            severity="information",
            timeout=5.0,
        )

    # --- Background Workers ---

    def on_troubleshooting_workspace_run_diagnosis_requested(
        self, event: TroubleshootingWorkspace.RunDiagnosisRequested
    ) -> None:
        if self.is_busy:
            workspace = self.query_one("#troubleshooting-workspace", TroubleshootingWorkspace)
            workspace.append_log("[bold yellow]Aviso: Una operación de red ya está en ejecución.[/]")
            return
        self._execute_troubleshooting_worker(device=event.device, symptom=event.symptom, mode=event.mode)

    @work(thread=True)
    def _execute_troubleshooting_worker(self, device: DeviceInventory, symptom: str, mode: str) -> None:
        self.is_busy = True
        workspace = self.query_one("#troubleshooting-workspace", TroubleshootingWorkspace)
        self.call_from_thread(workspace.set_busy_state, True)
        self.call_from_thread(workspace.reset_progress, f"Iniciando sesión en {device.host}...")
        workspace.append_log(f"[bold cyan][>] Iniciando troubleshooting en {device.host}...[/]")

        try:
            provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
            model = db.get_setting("ai_model") or settings.ai_model
            auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve

            encrypted_key = db.get_setting("gemini_api_key")
            if encrypted_key:
                decrypted_key = vault.decrypt(encrypted_key)
                if decrypted_key:
                    import os

                    os.environ["GEMINI_API_KEY"] = decrypted_key

            observer = TextualAgentObserver(app=self, workspace=workspace)
            agent = NetworkAssistantAgent(
                ai_provider=provider,
                ai_model=model,
                auto_approve=auto_approve,
                observer=observer,
            )

            if mode == "PROACTIVE":
                agent.execute_troubleshooting(device=device, symptom=symptom)
            else:
                telemetry = TelemetryEvent(raw_text=symptom, source_host=device.host)
                agent.process_telemetry(device=device, telemetry=telemetry, mode=mode)
        except Exception as e:
            self.call_from_thread(workspace.update_progress, 100, f"Error: {e}")
            self.call_from_thread(workspace.append_log, f"[bold red]Error fatal en troubleshooting: {e}[/]")
        finally:
            self.is_busy = False
            self.call_from_thread(workspace.set_busy_state, False)
            self.call_from_thread(self._refresh_audit)

    def on_configuration_view_run_configuration_requested(
        self, event: ConfigurationView.RunConfigurationRequested
    ) -> None:
        if self.is_busy:
            workspace = self.query_one("#configuration-workspace", ConfigurationView)
            workspace.append_log("[bold yellow]Aviso: Una operación de red ya está en ejecución.[/]")
            return
        self._execute_configuration_worker(
            device=event.device, natural_request=event.natural_request, protocol_hint=event.protocol_hint
        )

    @work(thread=True)
    def _execute_configuration_worker(
        self, device: DeviceInventory, natural_request: str, protocol_hint: Optional[str]
    ) -> None:
        self.is_busy = True
        workspace = self.query_one("#configuration-workspace", ConfigurationView)
        workspace.append_log(f"[bold cyan][>] Sintetizando configuración para {device.host}...[/]")

        try:
            provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
            model = db.get_setting("ai_model") or settings.ai_model
            auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve

            observer = TextualAgentObserver(app=self, workspace=workspace)
            agent = NetworkAssistantAgent(
                ai_provider=provider,
                ai_model=model,
                auto_approve=auto_approve,
                observer=observer,
            )

            intent = agent.execute_configuration(
                device=device, natural_request=natural_request, protocol_hint=protocol_hint
            )
            if intent:
                self.call_from_thread(workspace.display_plan, intent)
        except Exception as e:
            self.call_from_thread(workspace.append_log, f"[bold red]Error durante configuración: {e}[/]")
        finally:
            self.is_busy = False
            self.call_from_thread(self._refresh_audit)

    def on_automation_view_run_batch_deployment_requested(
        self, event: AutomationView.RunBatchDeploymentRequested
    ) -> None:
        if self.is_busy:
            workspace = self.query_one("#automation-workspace", AutomationView)
            workspace.append_log("[bold yellow]Aviso: Una operación de red ya está en ejecución.[/]")
            return
        self._execute_batch_deployment_worker(
            devices=event.devices, script_content=event.script_content, vendor_family=event.vendor_family
        )

    @work(thread=True)
    def _execute_batch_deployment_worker(
        self, devices: List[DeviceInventory], script_content: str, vendor_family: str
    ) -> None:
        self.is_busy = True
        workspace = self.query_one("#automation-workspace", AutomationView)
        workspace.append_log(f"[bold cyan][>] Iniciando despliegue en lote sobre {len(devices)} equipos...[/]")

        try:
            deployer = BatchDeployer(observer=workspace)
            deployer.deploy_to_devices(devices=devices, raw_script=script_content, vendor_family=vendor_family)
        except Exception as e:
            self.call_from_thread(workspace.append_log, f"[bold red]Error en lote: {e}[/]")
        finally:
            self.is_busy = False
            self.call_from_thread(self._refresh_audit)

    def _refresh_audit(self) -> None:
        try:
            audit = self.query_one(AuditTableWidget)
            audit.reload_audit_data()
        except Exception:
            pass


def run_tui() -> None:
    """Launch the reactive Textual TUI interface."""
    app = NetworkingAgentTUIApp()
    app.run()


if __name__ == "__main__":
    run_tui()
