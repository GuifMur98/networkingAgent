"""Diagnostic and remediation console workspace widget."""

from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Log, RadioButton, RadioSet, Static, TextArea

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


class DiagnosticWorkspace(Widget):
    """Main operational diagnostic workspace combining proactive and reactive flows."""

    class RunDiagnosisRequested(Message):
        """Emitted when the operator triggers the diagnostic workflow."""

        def __init__(self, device: DeviceInventory, symptom: str, mode: str):
            super().__init__()
            self.device = device
            self.symptom = symptom
            self.mode = mode

    class ReturnHomeRequested(Message):
        """Emitted when the operator wants to return to the Home/Inicio view."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_device: Optional[DeviceInventory] = None
        self.selected_mode: str = "PROACTIVE"

    def compose(self) -> ComposeResult:
        with Vertical(id="diagnostic-container"):
            # Navigation Header with Back button
            with Horizontal(id="diagnostic-nav-bar"):
                yield Label("DIAGNOSTICO Y REMEDIACION ASISTIDA", id="diagnostic-title")
                yield Button("[ Volver al Inicio ]", id="btn-back-to-home")

            # Selected Device Card
            yield Static(id="target-device-card")

            # Mode Selector
            with Horizontal(id="mode-selector-bar", classes="section-panel"):
                yield Label("Modo:", id="lbl-mode")
                with RadioSet(id="radio-mode"):
                    yield RadioButton("Proactivo (Sondeo en vivo)", value=True, id="mode-proactive")
                    yield RadioButton("Reactivo (Syslog / Telemetria)", value=False, id="mode-reactive")

            # Quick Symptom Templates
            yield Label("Atajos de Sintomas:", id="lbl-quick-symptoms")
            with Horizontal(classes="symptom-chips"):
                yield Button("OSPF MTU Mismatch", id="chip-ospf", classes="chip-btn")
                yield Button("Duplex Mismatch", id="chip-duplex", classes="chip-btn")
                yield Button("BGP Neighbor Down", id="chip-bgp", classes="chip-btn")
                yield Button("Link Flapping", id="chip-flap", classes="chip-btn")

            # Symptom / Telemetry Input
            yield Label("Descripcion del Sintoma o Registro de Syslog:", id="lbl-symptom")
            yield TextArea(
                id="symptom-input",
                text="El switch presenta perdida de paquetes y errores en el enlace ether2.",
            )

            # Trigger Button
            yield Button("[ Ejecutar Diagnostico y Remediacion ]", id="btn-run-remediation", variant="primary")

            # AI Diagnosis Summary Static Panel
            yield Static(id="diagnosis-result")

            # Real-time Execution Log Output
            yield Label("Consola de Operaciones en Tiempo Real:", id="lbl-console")
            yield Log(id="log-terminal", highlight=True)

    def set_device(self, device: DeviceInventory) -> None:
        """Update target device display."""
        self.current_device = device
        card = self.query_one("#target-device-card", Static)
        text = Text()
        text.append("EQUIPO ACTIVO: ", style="bold cyan")
        text.append(f"{device.host} ", style="bold white")
        text.append(f"[{device.device_type}]", style="bold green")
        text.append(f" | Puerto: {device.port} | Usuario: {device.username}", style="dim")
        card.update(text)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "radio-mode":
            if event.pressed.id == "mode-proactive":
                self.selected_mode = "PROACTIVE"
            else:
                self.selected_mode = "REACTIVE"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back-to-home":
            self.post_message(self.ReturnHomeRequested())
            return

        text_area = self.query_one("#symptom-input", TextArea)

        # Handle quick chips
        if event.button.id == "chip-ospf":
            text_area.text = "Vecindad OSPF atascada en estado INIT/EXSTART debido a MTU mismatch en Ethernet1/1."
            return
        if event.button.id == "chip-duplex":
            text_area.text = "El switch presenta perdida de paquetes y errores en el enlace ether2 por duplex mismatch."
            return
        if event.button.id == "chip-bgp":
            text_area.text = "BGP neighbor 10.0.0.1 caido en estado Active/Idle, se requiere verificar conectividad."
            return
        if event.button.id == "chip-flap":
            text_area.text = "Interfaz Gi0/1 sufre caidas intermitentes (flapping frecuente) y requiere estabilizacion."
            return

        if event.button.id == "btn-run-remediation":
            if not self.current_device:
                self.append_log("[bold red]Error: Debe seleccionar un dispositivo en el panel lateral.[/bold red]")
                return
            symptom_text = text_area.text.strip()
            if not symptom_text:
                self.append_log(
                    "[bold yellow]Aviso: Ingrese un sintoma o mensaje de telemetria para analizar.[/bold yellow]"
                )
                return

            self.post_message(
                self.RunDiagnosisRequested(
                    device=self.current_device,
                    symptom=symptom_text,
                    mode=self.selected_mode,
                )
            )

    def append_log(self, message: str) -> None:
        """Write to execution log console."""
        log_widget = self.query_one("#log-terminal", Log)
        log_widget.write_line(message)

    def display_diagnosis(self, intent: NetworkIntent) -> None:
        """Render AI Diagnosis table into findings panel."""
        result_box = self.query_one("#diagnosis-result", Static)
        table = Table(title="Evaluacion Diagnostica del Cerebro de IA", expand=True)
        table.add_column("Propiedad", style="dim cyan", width=22)
        table.add_column("Detalle Analitico", style="bold white")

        sev_color = "red" if intent.severity == "CRITICAL" else "yellow"
        table.add_row("Severidad", f"[{sev_color}]{intent.severity}[/{sev_color}]")
        table.add_row("Causa Raiz", intent.diagnosis)
        table.add_row("Accion Propuesta", f"[yellow]{intent.action}[/yellow]")
        table.add_row("Requiere Configuracion", str(intent.requires_config_change))
        if intent.target_interface:
            table.add_row("Interfaz Destino", f"[bold green]{intent.target_interface}[/bold green]")
        if intent.mtu_value:
            table.add_row("Valor MTU", str(intent.mtu_value))
        if intent.bgp_neighbor_ip:
            table.add_row("Vecino BGP IP", intent.bgp_neighbor_ip)

        result_box.update(table)

    def display_no_op(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        result_box = self.query_one("#diagnosis-result", Static)
        panel = Panel(
            f"[bold green]EVALUACION DIAGNOSTICA TECNICA COMPLETADA[/bold green]\n\n"
            f"[bold cyan]Diagnostico de Causa Raiz:[/bold cyan]\n"
            f"{intent.diagnosis}\n\n"
            f"[bold yellow]Estado de Configuracion:[/bold yellow] No se requieren cambios en el equipo.\n"
            f"[dim]Severidad: {intent.severity} | Accion: {intent.action} | Equipo: {device.host}[/dim]",
            title="INFORME OPERACIONAL DEL ASISTENTE",
            border_style="green",
        )
        result_box.update(panel)

    def display_guardrail_block(self, intent: NetworkIntent, reason: str) -> None:
        result_box = self.query_one("#diagnosis-result", Static)
        panel = Panel(
            f"[bold red]ACCION BLOQUEADA POR GUARDARRAIL DE SEGURIDAD (BLAST RADIUS)[/bold red]\n\n"
            f"[yellow]El cerebro de IA propuso una modificacion de riesgo:[/yellow]\n"
            f"  * Accion solicitada: [bold red]{intent.action}[/bold red]\n"
            f"  * Interfaz Objetivo: [bold yellow]{intent.target_interface or 'N/A'}[/bold yellow]\n\n"
            f"[bold cyan]Motivo de Proteccion:[/bold cyan]\n"
            f"{reason}\n\n"
            f"[green]Recomendacion:[/green]\n"
            f"Las interfaces criticas de enlace ascendente estan blindadas contra reinicios.",
            title="SEGURIDAD ACTIVA: PROTECCION DE INFRAESTRUCTURA",
            border_style="red",
        )
        result_box.update(panel)
