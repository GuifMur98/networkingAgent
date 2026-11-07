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
        Binding("1", "nav_troubleshooting", "Troubleshooting", show=False),
        Binding("2", "nav_configuration", "Configuración", show=False),
        Binding("3", "nav_automation", "Automatización", show=False),
        Binding("4", "nav_inventory", "Inventario", show=False),
        Binding("5", "nav_audit", "Auditoría", show=False),
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

            # 5 Action Cards in Responsive Grid
            with Grid(id="home-action-grid"):
                yield Button(
                    "1. TROUBLESHOOTING\nDiagnóstico autónomo y análisis de causa raíz en lenguaje natural",
                    id="btn-nav-troubleshooting",
                    classes="home-nav-card card-troubleshooting",
                )
                yield Button(
                    "2. CONFIGURACION\nAprovisionamiento de BGP, OSPF, VLAN, ACLs en lenguaje natural",
                    id="btn-nav-configuration",
                    classes="home-nav-card card-configuration",
                )
                yield Button(
                    "3. AUTOMATIZACION\nEditor de plantillas, validación sintáctica y despliegue masivo",
                    id="btn-nav-automation",
                    classes="home-nav-card card-automation",
                )
                yield Button(
                    "4. INVENTARIO DE EQUIPOS\nCatálogo de routers, alta y prueba de conectividad",
                    id="btn-nav-inventory",
                    classes="home-nav-card card-inventory",
                )
                yield Button(
                    "5. REGISTRO DE AUDITORIA\nBitácora inmutable de cambios, eventos y rollbacks",
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
            "[bold green]ACTIVO (Confirmación Requerida)[/bold green]"
            if not auto_approve
            else "[bold red]DESACTIVADO (Auto-Approve ON)[/bold red]"
        )

        status_text = (
            f"[bold cyan]ESTADO DEL SISTEMA:[/bold cyan]\n"
            f"  * Proveedor de IA: [bold white]{provider.upper()}[/] ([dim]{model}[/])\n"
            f"  * Dispositivos Registrados: [bold white]{len(devices)} equipos en SQLite[/]\n"
            f"  * Control Humano (HitL): {hitl_status}\n\n"
            f"[dim]Seleccione una opción [1-5], use atajos de teclado o presione [S] para Ajustes de IA.[/dim]"
        )

        panel = Panel(
            status_text,
            title="PANEL DE CONTROL OPERACIONAL",
            border_style="cyan",
            padding=(0, 1),
        )
        card.update(panel)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["btn-nav-troubleshooting", "btn-nav-diagnostic"]:
            self.post_message(self.NavigateToTab("pane-troubleshooting"))
        elif event.button.id == "btn-nav-configuration":
            self.post_message(self.NavigateToTab("pane-configuration"))
        elif event.button.id == "btn-nav-automation":
            self.post_message(self.NavigateToTab("pane-automation"))
        elif event.button.id == "btn-nav-inventory":
            self.post_message(self.NavigateToTab("pane-inventory"))
        elif event.button.id == "btn-nav-audit":
            self.post_message(self.NavigateToTab("pane-audit"))

    def action_nav_troubleshooting(self) -> None:
        self.post_message(self.NavigateToTab("pane-troubleshooting"))

    def action_nav_configuration(self) -> None:
        self.post_message(self.NavigateToTab("pane-configuration"))

    def action_nav_automation(self) -> None:
        self.post_message(self.NavigateToTab("pane-automation"))

    def action_nav_inventory(self) -> None:
        self.post_message(self.NavigateToTab("pane-inventory"))

    def action_nav_audit(self) -> None:
        self.post_message(self.NavigateToTab("pane-audit"))
