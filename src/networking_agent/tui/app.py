"""Main reactive Textual TUI application for NetworkingAgent."""

import threading
from typing import List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, TabbedContent, TabPane

from networking_agent.core.config import settings
from networking_agent.core.crypto import vault
from networking_agent.core.db import db
from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.engine.observer import AgentObserver
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.models.telemetry import TelemetryEvent
from networking_agent.tui.modals.device_modal import DeviceModal
from networking_agent.tui.modals.hitl_modal import HitLModal
from networking_agent.tui.modals.vault_modal import VaultModal
from networking_agent.tui.widgets.audit_table import AuditTableWidget
from networking_agent.tui.widgets.device_sidebar import DeviceSidebar
from networking_agent.tui.widgets.diagnostic_view import DiagnosticWorkspace
from networking_agent.tui.widgets.status_bar import TopStatusBar


class TextualAgentObserver(AgentObserver):
    """Bridge observer connecting NetworkAssistantAgent events to Textual widgets."""

    def __init__(self, app: "NetworkingAgentTUIApp", workspace: DiagnosticWorkspace):
        self.app = app
        self.workspace = workspace

    def _safe_call(self, callback, *args, **kwargs) -> None:
        """Call a UI method safely regardless of whether we are in main loop or worker thread."""
        if getattr(self.app, "_thread_id", None) == threading.get_ident():
            callback(*args, **kwargs)
        else:
            self.app.call_from_thread(callback, *args, **kwargs)

    def on_status_update(self, message: str) -> None:
        self._safe_call(self.workspace.append_log, f"[*] {message}")

    def on_diagnosis_ready(self, intent: NetworkIntent) -> None:
        self._safe_call(self.workspace.display_diagnosis, intent)
        self._safe_call(
            self.workspace.append_log,
            f"[bold cyan]AI Diagnosis:[/] {intent.diagnosis} (Severity: {intent.severity})",
        )

    def on_no_op_required(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        self._safe_call(self.workspace.display_no_op, device, intent)
        self._safe_call(
            self.workspace.append_log,
            "[bold green]✔ Evaluación diagnóstica finalizada: No se requieren cambios en la configuración.[/]",
        )

    def on_guardrail_blocked(self, intent: NetworkIntent, reason: str) -> None:
        self._safe_call(self.workspace.display_guardrail_block, intent, reason)
        self._safe_call(
            self.workspace.append_log,
            f"[bold red]🛑 Guardarraíl activado: {reason}[/]",
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
        self._safe_call(self.workspace.append_log, step)

    def on_completion(self, success: bool, message: str) -> None:
        color = "bold green" if success else "bold red"
        self._safe_call(self.workspace.append_log, f"[{color}]{message}[/{color}]")


class NetworkingAgentTUIApp(App):
    """Main terminal user interface application for NetworkingAgent."""

    TITLE = "NetworkingAgent Enterprise AI"
    SUB_TITLE = "Autonomous & Closed-Loop Network Assistant"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Salir", show=True),
        Binding("d", "add_device", "Añadir Equipo", show=True),
        Binding("s", "open_settings", "Ajustes IA", show=True),
        Binding("r", "refresh_all", "Recargar", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_busy = False

    def compose(self) -> ComposeResult:
        # Load configuration preferences
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

        with TabbedContent(id="main-tabs"):
            with TabPane("🔍 Asistente y Diagnóstico", id="pane-diagnostic"):
                with Horizontal(id="main-split"):
                    yield DeviceSidebar(id="device-sidebar")
                    yield DiagnosticWorkspace(id="diagnostic-workspace")

            with TabPane("📋 Registro de Auditoría", id="pane-audit"):
                yield AuditTableWidget(id="audit-widget")

        yield Footer()

    def on_mount(self) -> None:
        """Trigger initial device sync."""
        sidebar = self.query_one(DeviceSidebar)
        sidebar.reload_devices()

    def on_device_sidebar_device_selected(self, event: DeviceSidebar.DeviceSelected) -> None:
        """Route selected device to workspace."""
        workspace = self.query_one(DiagnosticWorkspace)
        workspace.set_device(event.device)

    def on_device_sidebar_add_device_requested(self, event: DeviceSidebar.AddDeviceRequested) -> None:
        self.action_add_device()

    def action_add_device(self) -> None:
        """Display DeviceModal to register a new host."""
        def on_device_added(device: Optional[DeviceInventory]) -> None:
            if device:
                sidebar = self.query_one(DeviceSidebar)
                sidebar.reload_devices()
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

        self.push_screen(VaultModal(), callback=on_settings_saved)

    def action_refresh_all(self) -> None:
        """Reload inventory and audit log."""
        sidebar = self.query_one(DeviceSidebar)
        sidebar.reload_devices()
        audit_widget = self.query_one(AuditTableWidget)
        audit_widget.reload_audit_data()
        status_bar = self.query_one(TopStatusBar)
        status_bar.update_device_count(len(db.list_devices()))

    def on_diagnostic_workspace_run_diagnosis_requested(
        self, event: DiagnosticWorkspace.RunDiagnosisRequested
    ) -> None:
        """Handler for running the diagnostic closed-loop workflow."""
        if self.is_busy:
            workspace = self.query_one(DiagnosticWorkspace)
            workspace.append_log("[bold yellow]Aviso: Una operación de red ya está en ejecución.[/]")
            return

        self._execute_remediation_worker(
            device=event.device,
            symptom=event.symptom,
            mode=event.mode,
        )

    @work(thread=True)
    def _execute_remediation_worker(self, device: DeviceInventory, symptom: str, mode: str) -> None:
        """Runs the long-running Netmiko SSH and AI inference in a background thread."""
        self.is_busy = True
        workspace = self.query_one(DiagnosticWorkspace)
        workspace.append_log(f"[bold cyan]▶ Iniciando análisis [{mode}] en {device.host}...[/]")

        try:
            # Load active configuration
            provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
            model = db.get_setting("ai_model") or settings.ai_model
            auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve

            # Decrypt Gemini key if configured in SQLite
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

            telemetry = TelemetryEvent(raw_text=symptom, source_host=device.host)
            agent.process_telemetry(device=device, telemetry=telemetry, mode=mode)

        except Exception as e:
            self.call_from_thread(workspace.append_log, f"[bold red]Error fatal durante la remediación: {e}[/]")
        finally:
            self.is_busy = False
            # Refresh audit log table
            def refresh_audit():
                try:
                    audit = self.query_one(AuditTableWidget)
                    audit.reload_audit_data()
                except Exception:
                    pass

            self.call_from_thread(refresh_audit)


def run_tui() -> None:
    """Launch the reactive Textual TUI interface."""
    app = NetworkingAgentTUIApp()
    app.run()


if __name__ == "__main__":
    run_tui()
