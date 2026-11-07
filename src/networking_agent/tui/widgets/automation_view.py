"""Automation workspace widget with interactive TextArea editor, dry-run syntax validator, and batch deployment."""

from typing import List

from rich import box
from rich.panel import Panel
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Log, Select, SelectionList, Static, TextArea

from networking_agent.core.db import db
from networking_agent.engine.automation import TemplateEngine
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.config_intent import AutomationTemplate
from networking_agent.models.device import DeviceInventory


class AutomationView(Widget):
    """Full automation suite with interactive text editor, syntax checking, and multi-host deployment."""

    class RunBatchDeploymentRequested(Message):
        """Emitted when the operator requests mass deployment of the editor content."""

        def __init__(self, devices: List[DeviceInventory], script_content: str, vendor_family: str):
            super().__init__()
            self.devices = devices
            self.script_content = script_content
            self.vendor_family = vendor_family

    class ReturnHomeRequested(Message):
        """Emitted when returning to the home screen."""

    VENDOR_CHOICES = [
        ("Cisco IOS / IOS-XE", "cisco_ios"),
        ("Cisco NX-OS", "cisco_nxos"),
        ("Juniper Junos", "juniper_junos"),
        ("MikroTik RouterOS", "mikrotik_routeros"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.templates: List[AutomationTemplate] = TemplateEngine.get_templates()
        self.available_devices: List[DeviceInventory] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="automation-container"):
            # Header Navigation Bar
            with Horizontal(id="automation-top-bar"):
                yield Label("AUTOMATIZACION // EDITOR DE PLANTILLAS Y DESPLIEGUE MASIVO", id="automation-title")
                yield Button("Volver al Inicio", id="btn-back-from-automation")

            # Control Toolbar
            with Horizontal(id="automation-toolbar", classes="section-panel"):
                with Horizontal(id="automation-selectors"):
                    template_options = [
                        (t.name, t.name) for t in self.templates
                    ] + [("Script Personalizado / Directo", "custom")]
                    yield Label("Plantilla:", id="lbl-tpl-picker")
                    yield Select(
                        template_options,
                        value=self.templates[0].name,
                        id="select-template",
                        allow_blank=False,
                    )

                    yield Label("Fabricante:", id="lbl-vendor-picker")
                    yield Select(self.VENDOR_CHOICES, value="cisco_ios", id="select-vendor-auto", allow_blank=False)

                with Horizontal(id="automation-actions"):
                    yield Button("Validar Sintaxis (Dry-Run)", id="btn-validate-script")
                    yield Button("Desplegar en Equipos", id="btn-deploy-batch", variant="primary")

            # Main Workspace Split (Editor on Left, Device & Validation on Right)
            with Horizontal(id="automation-split"):
                with Vertical(id="editor-col"):
                    yield Label("Editor de Configuración / Script CLI (TextArea interactivo):", id="lbl-editor")
                    initial_text = self.templates[0].template_content if self.templates else ""
                    yield TextArea(
                        text=initial_text,
                        id="automation-editor",
                        language="yaml",
                        show_line_numbers=True,
                    )

                with Vertical(id="devices-and-status-col"):
                    yield Label("Equipos Destino para Despliegue:", id="lbl-target-devices")
                    yield SelectionList[str](id="device-selection-list")

                    yield Label("Diagnóstico de Sintaxis y Seguridad:", id="lbl-syntax-header")
                    yield Static(id="syntax-status-card")

            # Bottom Batch Execution Log Terminal
            yield Label("Consola de Despliegue Masivo y Rollback por Lote:", id="lbl-auto-console")
            yield Log(id="automation-log-terminal", highlight=True)

    def on_mount(self) -> None:
        self.reload_devices()
        self._run_syntax_validation()

    def reload_devices(self) -> None:
        """Loads available devices from SQLite into the checklist."""
        raw_devs = db.list_devices()
        self.available_devices = []
        selection_list = self.query_one("#device-selection-list", SelectionList)
        selection_list.clear_options()

        for idx, dev_dict in enumerate(raw_devs):
            dev = db.get_device_by_id(dev_dict["id"])
            if dev:
                self.available_devices.append(dev)
                label = f"{dev.host} ({dev.device_type}) [{dev.username}]"
                initial_val = idx == 0
                selection_list.add_option((label, dev.host, initial_val))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-template":
            chosen = str(event.value)
            editor = self.query_one("#automation-editor", TextArea)
            vendor_select = self.query_one("#select-vendor-auto", Select)

            for tpl in self.templates:
                if tpl.name == chosen:
                    editor.text = tpl.template_content
                    vendor_select.value = tpl.vendor_family
                    self._run_syntax_validation()
                    break
        elif event.select.id == "select-vendor-auto":
            self._run_syntax_validation()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back-from-automation":
            self.post_message(self.ReturnHomeRequested())
        elif event.button.id == "btn-validate-script":
            self._run_syntax_validation()
        elif event.button.id == "btn-deploy-batch":
            self._trigger_batch_deployment()

    def _run_syntax_validation(self) -> None:
        """Performs static syntax and guardrail analysis on the editor content."""
        editor = self.query_one("#automation-editor", TextArea)
        vendor_family = str(self.query_one("#select-vendor-auto", Select).value)
        status_card = self.query_one("#syntax-status-card", Static)

        report = ConfigSyntaxValidator.validate_script(editor.text, vendor_family=vendor_family)

        if report.is_valid:
            warn_text = f"\n[yellow]Avisos:[/yellow] {', '.join(report.warnings)}" if report.warnings else ""
            content = (
                f"[bold green][OK] SINTAXIS VALIDA (DRY-RUN EXITOSO)[/bold green]\n"
                f"  * Comandos identificados: {report.line_count}\n"
                f"  * Fabricante: {vendor_family}\n"
                f"  * Guardarraíles destructivos: 0 violaciones{warn_text}\n\n"
                f"[dim]El script está listo para su inyección segura.[/dim]"
            )
            panel = Panel(content, title="ANALISIS ESTATICO", border_style="#4ade80", box=box.ROUNDED)
        else:
            err_text = "\n".join([f"  * {err}" for err in report.errors])
            content = (
                f"[bold red][!] ERRORES DE SINTAXIS O SEGURIDAD DETECTADOS[/bold red]\n"
                f"{err_text}\n\n"
                f"[dim]Corrija los errores en el editor antes de continuar.[/dim]"
            )
            panel = Panel(content, title="BLOQUEO DE SEGURIDAD", border_style="#f43f5e", box=box.ROUNDED)

        status_card.update(panel)

    def _trigger_batch_deployment(self) -> None:
        """Collects selected targets and dispatches deployment message."""
        selection_list = self.query_one("#device-selection-list", SelectionList)
        selected_hosts = selection_list.selected

        if not selected_hosts:
            self.append_log("[bold red][!] Selecciona al menos un equipo de la lista para el despliegue.[/]")
            return

        targets = [d for d in self.available_devices if d.host in selected_hosts]
        editor = self.query_one("#automation-editor", TextArea)
        vendor_family = str(self.query_one("#select-vendor-auto", Select).value)

        # Validate syntax first
        report = ConfigSyntaxValidator.validate_script(editor.text, vendor_family=vendor_family)
        if not report.is_valid:
            self.append_log("[bold red][!] Corrige primero los errores de sintaxis antes de desplegar.[/]")
            return

        self.post_message(
            self.RunBatchDeploymentRequested(
                devices=targets,
                script_content=editor.text,
                vendor_family=vendor_family,
            )
        )

    def append_log(self, text: str) -> None:
        """Appends log lines to the batch log pane."""
        log = self.query_one("#automation-log-terminal", Log)
        try:
            from rich.text import Text
            log.write_line(Text.from_markup(text))
        except Exception:
            log.write_line(text)
