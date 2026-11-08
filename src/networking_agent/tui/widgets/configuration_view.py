"""Declarative natural-language configuration workspace widget."""

from typing import Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Log, ProgressBar, Static, TextArea

from networking_agent.models.config_intent import ConfigurationIntent, ProtocolConfigType
from networking_agent.models.device import DeviceInventory


class ConfigurationView(Widget):
    """Interactive workspace for natural-language multi-protocol provisioning."""

    class RunConfigurationRequested(Message):
        """Emitted when the operator requests configuration synthesis and deployment."""

        def __init__(self, device: DeviceInventory, natural_request: str, protocol_hint: Optional[str] = None):
            super().__init__()
            self.device = device
            self.natural_request = natural_request
            self.protocol_hint = protocol_hint

    class ReturnHomeRequested(Message):
        """Emitted when operator wants to return to the home screen."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_device: Optional[DeviceInventory] = None
        self.selected_protocol: Optional[str] = "vlan"

    def compose(self) -> ComposeResult:
        with Vertical(id="configuration-container"):
            with Vertical(id="config-content-wrapper", classes="workspace-content-wrapper"):
                # Navigation Header with Back button
                with Horizontal(id="config-nav-bar"):
                    yield Label("CONFIGURACION // APROVISIONAMIENTO EN LENGUAJE NATURAL", id="config-title")
                    yield Button("Volver al Inicio", id="btn-back-from-config")

                # Selected Device Card
                yield Static(id="config-target-card")

                # Protocol Focus / Quick Category Selectors (Organized in two responsive rows)
                yield Label(
                    "Atajos de Protocolos y Servicios (Clic para autocompletar requerimiento):",
                    id="lbl-config-proto",
                )
                with Vertical(id="proto-chips-container"):
                    with Horizontal(classes="proto-chips-row"):
                        yield Button("BGP", id="chip-proto-bgp", classes="chip-btn")
                        yield Button("OSPF", id="chip-proto-ospf", classes="chip-btn")
                        yield Button("EIGRP", id="chip-proto-eigrp", classes="chip-btn")
                        yield Button("Enrutamiento Dinámico", id="chip-proto-dynamic", classes="chip-btn")
                    with Horizontal(classes="proto-chips-row"):
                        yield Button("VLAN & Trunk", id="chip-proto-vlan", classes="chip-btn")
                        yield Button("Port-Channel / LACP", id="chip-proto-channel", classes="chip-btn")
                        yield Button("Seguridad / ACL", id="chip-proto-acl", classes="chip-btn")
                        yield Button("Servicios (NTP/Syslog)", id="chip-proto-services", classes="chip-btn")

                # Natural Language Requirement Input
                yield Label(
                    "Descripción del Requerimiento de Configuración (Obligatorio *):",
                    id="lbl-config-prompt",
                )
                placeholder_msg = (
                    "Escribe la configuración deseada en lenguaje natural (ej: 'Agrega la red 10.50.0.0/24 "
                    "al protocolo de enrutamiento dinámico', 'Crea la VLAN 100 llamada DATOS en modo access en Gi0/5 "
                    "con su SVI 192.168.100.1/24') o selecciona un atajo superior..."
                )
                yield TextArea(
                    id="config-request-input",
                    text="",
                    placeholder=placeholder_msg,
                )

                # Trigger Button
                yield Button(
                    "Sintetizar y Aplicar Configuración Segura",
                    id="btn-run-config",
                    variant="primary",
                )

                # Candidate Plan, Diff & Conflict Preview Panel
                yield Static(id="config-plan-result")

                # Real-time Execution Log Output & Live Progress Indicator
                with Vertical(id="config-progress-container"):
                    with Horizontal(id="config-progress-header"):
                        yield Label("Consola de Despliegue y Verificación en Tiempo Real:", id="lbl-config-console")
                        yield Label("[dim]Esperando requerimiento[/dim]", id="lbl-config-step")
                        yield Label("[bold #00e5ff]0%[/]", id="lbl-config-pct")
                    yield ProgressBar(id="config-progress-bar", total=100, show_eta=False, show_percentage=False)

                yield Log(id="config-log-terminal", highlight=True)

    def set_device(self, device: DeviceInventory) -> None:
        """Sets active target device for configuration."""
        self.current_device = device
        card = self.query_one("#config-target-card", Static)
        text = Text()
        text.append("EQUIPO DESTINO: ", style="bold cyan")
        text.append(f"{device.host} ", style="bold white")
        text.append(f"[{device.device_type}]", style="bold green")
        text.append(f" | Puerto: {device.port} | Usuario: {device.username}", style="dim")
        card.update(text)

    def update_progress(self, percentage: int, step: str) -> None:
        """Update live execution progress bar and step description."""
        try:
            bar = self.query_one("#config-progress-bar", ProgressBar)
            bar.update(progress=percentage)
            lbl_step = self.query_one("#lbl-config-step", Label)
            lbl_step.update(step)
            lbl_pct = self.query_one("#lbl-config-pct", Label)
            color = "#4ade80" if percentage >= 100 else "#00e5ff"
            lbl_pct.update(f"[bold {color}]{percentage}%[/]")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back-from-config":
            self.post_message(self.ReturnHomeRequested())
        elif event.button.id == "chip-proto-bgp":
            self.selected_protocol = ProtocolConfigType.BGP.value
            self._fill_example(
                "Configura BGP con AS 65100, vecino 10.0.0.2 con AS remoto 65200 y anuncia la red 192.168.10.0/24."
            )
        elif event.button.id == "chip-proto-ospf":
            self.selected_protocol = ProtocolConfigType.OSPF.value
            self._fill_example(
                "Configura OSPF proceso 1 con router-id 1.1.1.1 en el área 0 para la red 10.0.0.0/16."
            )
        elif event.button.id == "chip-proto-eigrp":
            self.selected_protocol = ProtocolConfigType.EIGRP.value
            self._fill_example(
                "Activa EIGRP con AS 100 para la red 172.16.0.0/16 y desactiva auto-summary."
            )
        elif event.button.id == "chip-proto-dynamic":
            self.selected_protocol = "dynamic_routing"
            self._fill_example(
                "Agrega la nueva red 10.50.0.0/24 al protocolo de enrutamiento dinámico activo en el equipo."
            )
        elif event.button.id == "chip-proto-vlan":
            self.selected_protocol = ProtocolConfigType.VLAN.value
            self._fill_example(
                "Crea la VLAN 100 con nombre 'DATOS' y configúrala en modo access en Gi0/5 con su SVI 192.168.100.1/24."
            )
        elif event.button.id == "chip-proto-channel":
            self.selected_protocol = ProtocolConfigType.PORT_CHANNEL.value
            self._fill_example(
                "Crea un Port-Channel 5 LACP con Gi0/1 y Gi0/2 en modo trunk permitiendo VLAN 10,20."
            )
        elif event.button.id == "chip-proto-acl":
            self.selected_protocol = ProtocolConfigType.ACL.value
            self._fill_example(
                "Crea una ACL extendida 'BLOQUEAR-TELNET' bloqueando TCP 23 pero permitiendo el resto del tráfico IP."
            )
        elif event.button.id == "chip-proto-services":
            self.selected_protocol = ProtocolConfigType.SERVICES.value
            self._fill_example(
                "Configura el servidor NTP en 10.10.10.123 y el servidor Syslog remoto en 10.10.10.514."
            )
        elif event.button.id == "btn-run-config":
            self._trigger_configuration()

    def _fill_example(self, prompt_text: str) -> None:
        input_box = self.query_one("#config-request-input", TextArea)
        input_box.text = prompt_text

    def _trigger_configuration(self) -> None:
        if not self.current_device:
            self.append_log("[bold red][!] Selecciona primero un equipo de la barra lateral izquierda.[/]")
            return

        text = self.query_one("#config-request-input", TextArea).text.strip()
        if not text:
            self.append_log(
                "[bold red][!] El campo de requerimiento de configuración es obligatorio. "
                "Escribe una instrucción o selecciona un atajo superior.[/]"
            )
            return

        panel_widget = self.query_one("#config-plan-result", Static)
        panel_widget.styles.display = "none"
        panel_widget.update("")
        self.update_progress(0, "[dim]Iniciando síntesis y verificación...[/dim]")

        self.post_message(
            self.RunConfigurationRequested(
                device=self.current_device,
                natural_request=text,
                protocol_hint=self.selected_protocol,
            )
        )

    def append_log(self, text: str) -> None:
        """Appends log lines to the configuration terminal pane."""
        log = self.query_one("#config-log-terminal", Log)
        try:
            from rich.text import Text
            log.write_line(Text.from_markup(text))
        except Exception:
            log.write_line(text)

    def display_plan(self, config_intent: ConfigurationIntent) -> None:
        """Renders the synthesized configuration plan, active state, candidate diff, and conflict analysis."""
        panel_widget = self.query_one("#config-plan-result", Static)
        panel_widget.styles.display = "block"
        table = Table(
            title=f"PLAN DE CONFIGURACION: {config_intent.protocol_type.value.upper()}",
            show_header=True,
            header_style="bold #00e5ff",
        )
        table.add_column("Sección", style="dim", width=24)
        table.add_column("Detalle / Comandos CLI", style="bold white")

        table.add_row("Descripción Funcional", config_intent.description)
        table.add_row("Dispositivo Destino", config_intent.target_host or "Seleccionado")

        if config_intent.existing_state_summary:
            table.add_row("Estado Activo en Equipo", f"[cyan]{config_intent.existing_state_summary}[/cyan]")

        if config_intent.conflict_analysis:
            if "[!]" in config_intent.conflict_analysis:
                table.add_row(
                    "Análisis de Conflictos",
                    f"[bold yellow]{config_intent.conflict_analysis}[/bold yellow]",
                )
            else:
                table.add_row(
                    "Análisis de Conflictos",
                    f"[bold green]{config_intent.conflict_analysis}[/bold green]",
                )

        cmds_preview = "\n".join([f"+ {c}" for c in config_intent.candidate_commands])
        table.add_row("Comandos Candidatos (Diff)", f"[bold green]{cmds_preview}[/bold green]")

        if config_intent.verification_commands:
            verif_preview = "\n".join([f"* {c}" for c in config_intent.verification_commands])
            table.add_row("Verificación Post-Cambio", f"[cyan]{verif_preview}[/cyan]")

        if config_intent.rollback_commands:
            rb_preview = "\n".join([f"- {c}" for c in config_intent.rollback_commands])
            table.add_row("Plan de Rollback Inverso", f"[yellow]{rb_preview}[/yellow]")

        table.add_row("Notas de Seguridad", f"[white]{config_intent.safety_notes}[/white]")
        panel_widget.update(Panel(table, border_style="#00e5ff", box=box.ROUNDED))
