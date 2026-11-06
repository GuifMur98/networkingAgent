"""Welcome and home dashboard widget with typography banner and minimalist navigation cards."""

from rich.panel import Panel
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static

from networking_agent.core.config import settings
from networking_agent.core.db import db
from networking_agent.tui.widgets.banner_widget import BannerWidget


class HomeDashboard(Widget):
    """Main welcome screen with ASCII banner, operational summary, and action cards."""

    BINDINGS = [
        Binding("1", "nav_diagnostic", "Diagnostico", show=False),
        Binding("2", "nav_inventory", "Inventario", show=False),
        Binding("3", "nav_vault", "Ajustes IA", show=False),
        Binding("4", "nav_audit", "Auditoria", show=False),
    ]

    class NavigateToTab(Message):
        """Emitted when the operator clicks a quick action card to change tabs."""

        def __init__(self, tab_id: str):
            super().__init__()
            self.tab_id = tab_id

    class OpenSettingsRequested(Message):
        """Emitted when the operator requests the AI Vault settings modal."""

    def compose(self) -> ComposeResult:
        with Vertical(id="home-container"):
            # Minimalist ASCII Banner
            yield BannerWidget(id="home-banner")

            # Operational Status Card
            yield Static(id="home-status-card")

            # 4 Action Cards in Grid
            with Grid(id="home-action-grid"):
                yield Button(
                    "[1] DIAGNOSTICO Y REMEDIACION\nSondeo de interfaces y analisis de telemetria",
                    id="btn-nav-diagnostic",
                    classes="home-nav-card card-diagnostic",
                )
                yield Button(
                    "[2] INVENTARIO DE EQUIPOS\nCatalogo de routers, alta y prueba de conectividad",
                    id="btn-nav-inventory",
                    classes="home-nav-card card-inventory",
                )
                yield Button(
                    "[3] AJUSTES DE IA Y BOVEDA\nConfiguracion de proveedor, modelo y llaves de API",
                    id="btn-nav-vault",
                    classes="home-nav-card card-settings",
                )
                yield Button(
                    "[4] REGISTRO DE AUDITORIA\nBitacora inmutable de cambios y rollbacks",
                    id="btn-nav-audit",
                    classes="home-nav-card card-audit",
                )

    def on_mount(self) -> None:
        self.update_status_card()

    def update_status_card(self) -> None:
        """Render the system status summary panel."""
        card = self.query_one("#home-status-card", Static)
        provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
        model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:7b"
        devices = db.list_devices()
        auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve

        hitl_status = (
            "[bold green]ACTIVO (Confirmacion Requerida)[/bold green]"
            if not auto_approve
            else "[bold red]DESACTIVADO (Auto-Approve ON)[/bold red]"
        )

        status_text = (
            f"[bold cyan]ESTADO DEL SISTEMA:[/bold cyan]\n"
            f"  * Proveedor de IA: [bold white]{provider.upper()}[/] ([dim]{model}[/])\n"
            f"  * Dispositivos Registrados: [bold white]{len(devices)} equipos en SQLite[/]\n"
            f"  * Control Humano (HitL): {hitl_status}\n\n"
            f"[dim]Seleccione una opcion [1-4], use los atajos de teclado o presione [Q] para salir.[/dim]"
        )

        panel = Panel(
            status_text,
            title="PANEL DE CONTROL OPERACIONAL",
            border_style="cyan",
            padding=(0, 1),
        )
        card.update(panel)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-nav-diagnostic":
            self.post_message(self.NavigateToTab("pane-diagnostic"))
        elif event.button.id == "btn-nav-inventory":
            self.post_message(self.NavigateToTab("pane-inventory"))
        elif event.button.id == "btn-nav-vault":
            self.post_message(self.OpenSettingsRequested())
        elif event.button.id == "btn-nav-audit":
            self.post_message(self.NavigateToTab("pane-audit"))

    def action_nav_diagnostic(self) -> None:
        self.post_message(self.NavigateToTab("pane-diagnostic"))

    def action_nav_inventory(self) -> None:
        self.post_message(self.NavigateToTab("pane-inventory"))

    def action_nav_vault(self) -> None:
        self.post_message(self.OpenSettingsRequested())

    def action_nav_audit(self) -> None:
        self.post_message(self.NavigateToTab("pane-audit"))
