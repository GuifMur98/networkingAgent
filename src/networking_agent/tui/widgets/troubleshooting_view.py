"""Autonomous troubleshooting and root-cause resolution workspace."""

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


class TroubleshootingWorkspace(Widget):
    """Operational troubleshooting workspace combining live interrogation and natural language symptoms."""

    class RunDiagnosisRequested(Message):
        """Emitted when the operator triggers the troubleshooting workflow."""

        def __init__(self, device: DeviceInventory, symptom: str, mode: str):
            super().__init__()
            self.device = device
            self.symptom = symptom
            self.mode = mode

    class ReturnHomeRequested(Message):
        """Emitted when the operator requests returning to Home dashboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_device: Optional[DeviceInventory] = None
        self.selected_mode: str = "PROACTIVE"

    def compose(self) -> ComposeResult:
        with Vertical(id="diagnostic-container"):
            # Navigation Header with Back button
            with Horizontal(id="diagnostic-nav-bar"):
                yield Label("TROUBLESHOOTING // DIAGNOSTICO EN LENGUAJE NATURAL", id="diagnostic-title")
                yield Button("Volver al Inicio", id="btn-back-to-home")

            # Selected Device Card
            yield Static(id="target-device-card")

            # Mode Selector
            with Horizontal(id="mode-selector-bar", classes="section-panel"):
                yield Label("Modo de Interrogación:", id="lbl-mode")
                with RadioSet(id="radio-mode"):
                    yield RadioButton("Proactivo (Comandos show en vivo)", value=True, id="mode-proactive")
                    yield RadioButton("Reactivo (Análisis de Syslog/Logs)", value=False, id="mode-reactive")

            # Quick Symptom Templates
            yield Label("Atajos de Síntomas Comunes:", id="lbl-quick-symptoms")
            with Horizontal(classes="symptom-chips"):
                yield Button("BGP Down / Idle", id="chip-bgp", classes="chip-btn")
                yield Button("Duplex Mismatch", id="chip-duplex", classes="chip-btn")
                yield Button("Pérdida de Paquetes", id="chip-packetloss", classes="chip-btn")
                yield Button("OSPF MTU Mismatch", id="chip-ospf", classes="chip-btn")
                yield Button("VLAN Trunk Bloqueado", id="chip-vlan", classes="chip-btn")
                yield Button("Lentitud de Red", id="chip-slow", classes="chip-btn")

            # Symptom / Telemetry Input
            yield Label("Descripción del Síntoma Operacional (Lenguaje Natural):", id="lbl-symptom")
            yield TextArea(
                id="symptom-input",
                text="Los usuarios de la VLAN 20 reportan pérdida intermitente de paquetes hacia el gateway.",
            )

            # Trigger Button
            yield Button("Ejecutar Troubleshooting Autónomo", id="btn-run-remediation", variant="primary")

            # AI Diagnosis Summary Static Panel
            yield Static(id="diagnosis-result")

            # Real-time Execution Log Output
            yield Label("Consola de Interrogación y Telemetría en Tiempo Real:", id="lbl-console")
            yield Log(id="log-terminal", highlight=True)

    def set_device(self, device: DeviceInventory) -> None:
        """Update target device display."""
        self.current_device = device
        card = self.query_one("#target-device-card", Static)
        text = Text()
        text.append("EQUIPO SELECCIONADO: ", style="bold cyan")
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
        elif event.button.id == "chip-bgp":
            self._fill_symptom("El vecino BGP 10.0.0.2 no establece sesión y permanece en estado Idle / Active.")
        elif event.button.id == "chip-duplex":
            self._fill_symptom("duplex mismatch y colisiones tardías detectadas en la interfaz Gi0/1.")
        elif event.button.id == "chip-packetloss":
            self._fill_symptom("Pérdida recurrente de paquetes y errores CRC reportados en el enlace Gi0/1.")
        elif event.button.id == "chip-ospf":
            self._fill_symptom("Adyacencia OSPF en Gi0/1 estancada en estado EXSTART/EXCHANGE.")
        elif event.button.id == "chip-vlan":
            self._fill_symptom("El tráfico entre switches de la VLAN 100 no cruza el enlace troncal Gi0/2.")
        elif event.button.id == "chip-slow":
            self._fill_symptom("Los operadores reportan navegación lenta y latencia inusual en el segmento LAN.")
        elif event.button.id == "btn-run-remediation":
            self._trigger_run()

    def _fill_symptom(self, text: str) -> None:
        symptom_box = self.query_one("#symptom-input", TextArea)
        symptom_box.text = text

    def _trigger_run(self) -> None:
        if not self.current_device:
            self.append_log("[bold red][!] Selecciona primero un equipo de la barra lateral izquierda.[/]")
            return

        symptom = self.query_one("#symptom-input", TextArea).text.strip()
        if not symptom:
            self.append_log("[bold red][!] Describe el síntoma operacional antes de ejecutar el análisis.[/]")
            return

        self.post_message(
            self.RunDiagnosisRequested(
                device=self.current_device,
                symptom=symptom,
                mode=self.selected_mode,
            )
        )

    def append_log(self, text: str) -> None:
        """Appends log lines to the terminal pane."""
        log = self.query_one("#log-terminal", Log)
        log.write_line(text)

    def display_diagnosis(self, intent: NetworkIntent) -> None:
        """Renders the AI root-cause analysis panel."""
        panel_widget = self.query_one("#diagnosis-result", Static)
        table = Table(title="DICTAMEN TECNICO Y ANALISIS DE CAUSA RAIZ", show_header=True, header_style="bold cyan")
        table.add_column("Propiedad", style="dim", width=22)
        table.add_column("Detalle Diagnosticado", style="bold white")

        sev_color = "red" if intent.severity == "CRITICAL" else ("yellow" if intent.severity == "HIGH" else "green")
        table.add_row("Severidad del Incidente", f"[{sev_color}]{intent.severity}[/{sev_color}]")
        table.add_row("Diagnóstico Causa-Raíz", intent.diagnosis)
        table.add_row("Acción Técnica Sugerida", intent.action)
        table.add_row(
            "Requiere Cambio de Configuración",
            "[red]SI[/red]" if intent.requires_config_change else "[green]NO[/green]",
        )
        if intent.target_interface:
            table.add_row("Interfaz Afectada", intent.target_interface)
        if intent.mtu_value:
            table.add_row("Valor MTU", str(intent.mtu_value))
        if intent.bgp_neighbor_ip:
            table.add_row("IP Vecino BGP", intent.bgp_neighbor_ip)

        panel_widget.update(Panel(table, border_style="cyan"))

    def display_no_op(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        panel_widget = self.query_one("#diagnosis-result", Static)
        content = (
            f"[bold green]DIAGNOSTICO FINALIZADO: EQUIPO OPERACIONALMENTE SANO[/bold green]\n\n"
            f"El asistente determinó que [bold cyan]{device.host}[/bold cyan] no presenta fallas que requieran "
            f"modificación de configuración.\n\n"
            f"[bold]Explicación:[/bold] {intent.diagnosis}\n"
            f"[dim]No se aplicaron cambios. La investigación ha sido registrada en auditoría.[/dim]"
        )
        panel_widget.update(Panel(content, title="DICTAMEN TECNICO", border_style="green"))

    def display_guardrail_block(self, intent: NetworkIntent, reason: str) -> None:
        panel_widget = self.query_one("#diagnosis-result", Static)
        content = (
            f"[bold red]ACCION BLOQUEADA POR GUARDARRAIL DE SEGURIDAD OPERACIONAL[/bold red]\n\n"
            f"La acción propuesta fue interceptada para proteger la infraestructura crítica.\n"
            f"[bold]Motivo:[/bold] [yellow]{reason}[/yellow]\n"
            f"[dim]No se inyectaron comandos en el dispositivo.[/dim]"
        )
        panel_widget.update(Panel(content, title="SEGURIDAD Y PROTECCION ACTIVA", border_style="red"))


# Backward-compatibility alias
DiagnosticWorkspace = TroubleshootingWorkspace
