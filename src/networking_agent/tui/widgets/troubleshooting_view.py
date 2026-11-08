"""Autonomous troubleshooting and root-cause resolution workspace."""

from typing import Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Log, ProgressBar, RadioButton, RadioSet, Static, TextArea

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


class TroubleshootingWorkspace(Widget):
    """Operational troubleshooting workspace combining live interrogation and natural language symptoms."""

    MODE_DESCRIPTIONS = {
        "PROACTIVE": (
            "[bold #00e5ff]MODO PROACTIVO (RECOMENDADO PARA FALLAS ACTIVAS):[/] "
            "El agente se conectará vía SSH en tiempo real al equipo y ejecutará "
            "comandos de telemetría y salud ([#38bdf8]show interfaces, show ip route, show bgp, etc.[/]), "
            "combinando la salida viva con tu descripción para diagnosticar la causa raíz."
        ),
        "REACTIVE": (
            "[bold #fbbf24]MODO REACTIVO (FORENSE / HISTORICO):[/] "
            "El agente [bold underline]NO[/] enviará comandos ni tráfico al router. "
            "Analizará únicamente el texto o eventos de Syslog que ingreses en el campo "
            "inferior para correlacionar anomalías de incidentes ya ocurridos."
        ),
    }

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
            with Vertical(id="diagnostic-content-wrapper", classes="workspace-content-wrapper"):
                # Navigation Header with Back button
                with Horizontal(id="diagnostic-nav-bar"):
                    yield Label("TROUBLESHOOTING // DIAGNOSTICO EN LENGUAJE NATURAL", id="diagnostic-title")
                    yield Button("Volver al Inicio (h)", id="btn-back-to-home")

                # Selected Device Card
                yield Static(id="target-device-card")

                # Mode Selector Container
                with Vertical(id="mode-selector-container", classes="section-panel"):
                    with Horizontal(id="mode-selector-header"):
                        yield Label("Modo de Interrogación:", id="lbl-mode")
                        with RadioSet(id="radio-mode"):
                            yield RadioButton("Proactivo (Comandos show en vivo)", value=True, id="mode-proactive")
                            yield RadioButton("Reactivo (Análisis de Syslog/Logs)", value=False, id="mode-reactive")
                    yield Static(id="mode-description-banner")

                # Quick Symptom Templates
                yield Label(
                    "Atajos de Síntomas Comunes (Clic para autocompletar descripción):",
                    id="lbl-quick-symptoms",
                )
                with Vertical(id="symptom-chips-container"):
                    with Horizontal(classes="symptom-chips-row"):
                        yield Button("BGP Down / Idle", id="chip-bgp", classes="chip-btn")
                        yield Button("Duplex Mismatch", id="chip-duplex", classes="chip-btn")
                        yield Button("Pérdida de Paquetes", id="chip-packetloss", classes="chip-btn")
                    with Horizontal(classes="symptom-chips-row"):
                        yield Button("OSPF MTU Mismatch", id="chip-ospf", classes="chip-btn")
                        yield Button("VLAN Trunk Bloqueado", id="chip-vlan", classes="chip-btn")
                        yield Button("Lentitud de Red", id="chip-slow", classes="chip-btn")

                # Symptom / Telemetry Input
                yield Label("Descripción del Síntoma Operacional (Obligatorio *):", id="lbl-symptom")
                placeholder_msg = (
                    "Escribe el síntoma en lenguaje natural (ej: 'Vecino BGP 10.0.0.2 caído', "
                    "'Pérdida de paquetes en Gi0/1') o selecciona un atajo superior..."
                )
                yield TextArea(
                    id="symptom-input",
                    text="",
                    placeholder=placeholder_msg,
                )

                # Trigger Button
                yield Button("Ejecutar Troubleshooting Autónomo", id="btn-run-remediation", variant="primary")

                # AI Diagnosis Summary Static Panel
                yield Static(id="diagnosis-result")

                # Real-time Execution Log Output & Live Progress Indicator
                with Vertical(id="telemetry-progress-container"):
                    with Horizontal(id="telemetry-progress-header"):
                        yield Label("Consola de Interrogación y Telemetría en Tiempo Real:", id="lbl-console")
                        yield Label("[dim]Esperando ejecución[/dim]", id="lbl-telemetry-step")
                        yield Label("[bold #00e5ff]0%[/]", id="lbl-telemetry-pct")
                    yield ProgressBar(id="telemetry-progress-bar", total=100, show_eta=False, show_percentage=False)

                yield Log(id="log-terminal", highlight=True)

    def on_mount(self) -> None:
        self.update_mode_description()

    def update_mode_description(self) -> None:
        """Update explanatory banner based on active interrogation mode."""
        try:
            desc_widget = self.query_one("#mode-description-banner", Static)
            text = self.MODE_DESCRIPTIONS.get(self.selected_mode, "")
            desc_widget.update(Text.from_markup(text))
        except Exception:
            pass

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
            self.update_mode_description()

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
        symptom_box.focus()

    def _trigger_run(self) -> None:
        if not self.current_device:
            self.notify(
                "Selecciona primero un equipo de la barra lateral izquierda antes de iniciar el diagnóstico.",
                title="Equipo Requerido",
                severity="warning",
            )
            self.append_log("[bold red][!] Selecciona primero un equipo de la barra lateral izquierda.[/]")
            return

        symptom = self.query_one("#symptom-input", TextArea).text.strip()
        if not symptom:
            self.notify(
                "La descripción del síntoma operacional es obligatoria.",
                title="Campo Obligatorio",
                severity="warning",
            )
            self.append_log(
                "[bold red][!] Validación rechazada: Debes ingresar el síntoma antes de ejecutar.[/]"
            )
            self.query_one("#symptom-input", TextArea).focus()
            return

        # Hide previous diagnosis while new analysis runs
        panel_widget = self.query_one("#diagnosis-result", Static)
        panel_widget.styles.display = "none"
        panel_widget.update("")

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
        try:
            log.write_line(Text.from_markup(text))
        except Exception:
            log.write_line(text)

    def reset_progress(self, step: str = "En espera de diagnóstico") -> None:
        """Reset progress bar and percentage display to 0%."""
        try:
            bar = self.query_one("#telemetry-progress-bar", ProgressBar)
            bar.update(total=100, progress=0)
            lbl_pct = self.query_one("#lbl-telemetry-pct", Label)
            lbl_pct.update("[bold #00e5ff]0%[/]")
            lbl_step = self.query_one("#lbl-telemetry-step", Label)
            lbl_step.update(f"[dim]{step}[/dim]")
        except Exception:
            pass

    def update_progress(self, percentage: int, step: str) -> None:
        """Update live progress bar, percentage, and current phase description."""
        try:
            percentage = max(0, min(100, int(percentage)))
            bar = self.query_one("#telemetry-progress-bar", ProgressBar)
            bar.update(progress=percentage)

            lbl_pct = self.query_one("#lbl-telemetry-pct", Label)
            pct_color = "#4ade80" if percentage >= 100 else "#00e5ff"
            lbl_pct.update(f"[bold {pct_color}]{percentage}%[/]")

            lbl_step = self.query_one("#lbl-telemetry-step", Label)
            lbl_step.update(f"[dim cyan]●[/dim cyan] [white]{step}[/white]")
        except Exception:
            pass

    def set_busy_state(self, is_busy: bool) -> None:
        """Toggle action button state and label during live execution."""
        try:
            btn = self.query_one("#btn-run-remediation", Button)
            btn.disabled = is_busy
            btn.label = "Analizando Equipo..." if is_busy else "Ejecutar Troubleshooting Autónomo"
        except Exception:
            pass

    def display_diagnosis(self, intent: NetworkIntent) -> None:
        """Renders the AI root-cause analysis panel."""
        panel_widget = self.query_one("#diagnosis-result", Static)
        panel_widget.styles.display = "block"
        table = Table(title="DICTAMEN TECNICO Y ANALISIS DE CAUSA RAIZ", show_header=True, header_style="bold #00e5ff")
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

        panel_widget.update(Panel(table, border_style="#00e5ff", box=box.ROUNDED))

    def display_no_op(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        panel_widget = self.query_one("#diagnosis-result", Static)
        panel_widget.styles.display = "block"
        content = (
            f"[bold green]DIAGNOSTICO FINALIZADO: EQUIPO OPERACIONALMENTE SANO[/bold green]\n\n"
            f"El asistente determinó que [bold cyan]{device.host}[/bold cyan] no presenta fallas que requieran "
            f"modificación de configuración.\n\n"
            f"[bold]Explicación:[/bold] {intent.diagnosis}\n"
            f"[dim]No se aplicaron cambios. La investigación ha sido registrada en auditoría.[/dim]"
        )
        panel_widget.update(Panel(content, title="DICTAMEN TECNICO", border_style="#4ade80", box=box.ROUNDED))

    def display_guardrail_block(self, intent: NetworkIntent, reason: str) -> None:
        panel_widget = self.query_one("#diagnosis-result", Static)
        panel_widget.styles.display = "block"
        content = (
            f"[bold red]ACCION BLOQUEADA POR GUARDARRAIL DE SEGURIDAD OPERACIONAL[/bold red]\n\n"
            f"La acción propuesta fue interceptada para proteger la infraestructura crítica.\n\n"
            f"[bold]Motivo:[/bold] [yellow]{reason}[/yellow]\n"
            f"[dim]No se inyectaron comandos en el dispositivo.[/dim]"
        )
        panel = Panel(content, title="SEGURIDAD Y PROTECCION ACTIVA", border_style="#f43f5e", box=box.ROUNDED)
        panel_widget.update(panel)


# Backward-compatibility alias
DiagnosticWorkspace = TroubleshootingWorkspace
