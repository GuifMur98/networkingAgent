"""Human-in-the-Loop (HitL) authorization modal screen."""

from typing import List

from rich import box
from rich.panel import Panel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


class HitLModal(ModalScreen[bool]):
    """Modal dialog prompting the human operator to authorize or reject network changes."""

    BINDINGS = [
        Binding("y", "authorize", "Autorizar", show=True),
        Binding("n", "reject", "Rechazar", show=True),
        Binding("escape", "reject", "Cancelar", show=False),
    ]

    def __init__(
        self,
        device: DeviceInventory,
        intent: NetworkIntent,
        candidate_cli: List[str],
        rollback_info: str,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.device = device
        self.intent = intent
        self.candidate_cli = candidate_cli
        self.rollback_info = rollback_info

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-hitl-dialog"):
            target_display = self.intent.target_interface or self.intent.bgp_neighbor_ip or "N/A"
            sev_color = "red" if self.intent.severity == "CRITICAL" else "yellow"
            cli_preview = "\n".join([f"  + {c}" for c in self.candidate_cli])

            info_text = (
                f"[bold red]SOLICITUD DE AUTORIZACION (HUMAN-IN-THE-LOOP)[/bold red]\n\n"
                f"[bold]Dispositivo:[/bold] [cyan]{self.device.host}[/cyan] ({self.device.device_type}) | "
                f"[bold]Usuario:[/bold] [cyan]{self.device.username}[/cyan]\n"
                f"[bold]Accion:[/bold] [yellow]{self.intent.action}[/yellow] | "
                f"[bold]Objetivo:[/bold] [yellow]{target_display}[/yellow]\n"
                f"[bold]Severidad:[/bold] [{sev_color}]{self.intent.severity}[/{sev_color}]\n\n"
                f"[bold cyan]Diagnostico Tecnico:[/bold cyan]\n"
                f"{self.intent.diagnosis}\n\n"
                f"[bold yellow]Comandos a inyectar en el equipo:[/bold yellow]\n"
                f"[green]{cli_preview}[/green]\n\n"
                f"[bold white]Garantia de Rollback:[/bold white]\n"
                f"  * Snapshot previo de configuracion garantizado\n"
                f"  * Mecanismo: [dim]{self.rollback_info}[/dim]"
            )

            panel = Panel(
                info_text,
                title="CONTROL DE SEGURIDAD OPERACIONAL",
                border_style="#f43f5e",
                box=box.ROUNDED,
            )
            yield Static(panel, id="hitl-panel")

            with Horizontal(classes="modal-actions"):
                yield Button("Autorizar y Aplicar (Y)", id="btn-hitl-approve", variant="primary")
                yield Button("Rechazar y Abortar (N)", id="btn-hitl-reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-hitl-approve":
            self.action_authorize()
        elif event.button.id == "btn-hitl-reject":
            self.action_reject()

    def action_authorize(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
