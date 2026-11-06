"""Welcome and home dashboard widget with ASCII banner and quick navigation cards."""

from rich.panel import Panel
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.message import Message
from textual.widgets import Button, Static

from networking_agent.core.config import settings
from networking_agent.core.db import db
from networking_agent.tui.widgets.banner_widget import BannerWidget


class HomeDashboard(Static):
    """Main welcome screen with ASCII banner, operational summary, and action cards."""

    class NavigateToTab(Message):
        """Emitted when the operator clicks a quick action card to change tabs."""

        def __init__(self, tab_id: str):
            super().__init__()
            self.tab_id = tab_id

    class OpenSettingsRequested(Message):
        """Emitted when the operator requests the AI Vault settings modal."""

    def compose(self) -> ComposeResult:
        with Vertical(id="home-container"):
            # Prominent ASCII Banner
            yield BannerWidget(id="home-banner")

            # Quick Status Card
            yield Static(id="home-status-card")

            # 4 Big Action Cards in a Grid
            with Grid(id="home-action-grid"):
                yield Button(
                    "🚀 1. INICIAR DIAGNÓSTICO Y REMEDIACIÓN\n"
                    "Sondeo en vivo de equipos o análisis de Syslog con IA",
                    id="btn-nav-diagnostic",
                    classes="home-nav-card card-primary",
                )
                yield Button(
                    "🖥️ 2. GESTIONAR INVENTARIO DE EQUIPOS\n"
                    "Ver routers, registrar nuevos y probar credenciales",
                    id="btn-nav-inventory",
                    classes="home-nav-card card-secondary",
                )
                yield Button(
                    "🧠 3. CONFIGURACIÓN DE IA Y BÓVEDA\n"
                    "Elegir proveedor (Ollama/Gemini), modelo y API keys",
                    id="btn-nav-vault",
                    classes="home-nav-card card-settings",
                )
                yield Button(
                    "📋 4. HISTORIAL DE AUDITORÍA CRIPTOGRÁFICA\n"
                    "Revisar bitácora inmutable de remediaciones y rollbacks",
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

        hitl_status = "[bold yellow]🛡️ Human-in-the-Loop ACTIVO (Aprobación Requerida)[/]" if not auto_approve else "[bold red]⚠️ Auto-Approve ACTIVO[/]"

        status_text = (
            f"[bold cyan]ESTADO DEL SISTEMA:[/bold cyan]\n"
            f"• [bold]Cerebro de IA Activo:[/bold] [magenta]{provider.upper()}[/] ([bold]{model}[/])\n"
            f"• [bold]Dispositivos Enrolados en SQLite:[/bold] [green]{len(devices)} equipos[/]\n"
            f"• [bold]Seguridad & Control Humano:[/bold] {hitl_status}\n\n"
            f"[dim italic]Selecciona una de las 4 opciones a continuación o utiliza las teclas [1-4] / [q] para salir.[/dim italic]"
        )

        panel = Panel(
            status_text,
            title="📊 PANEL OPERACIONAL",
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
