"""Welcome and home dashboard widget with typography banner and cyberpunk mission control navigation cards."""

from typing import List, Optional

from rich import box
from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static

from networking_agent.core.config import settings
from networking_agent.core.db import db
from networking_agent.tui.widgets.banner_widget import BannerWidget


class HomeNavCard(Button):
    """Futuristic Cyberpunk / Mission Control navigation card for the 5 core modules."""

    DEFAULT_CSS = """
    HomeNavCard {
        width: 1fr;
        height: 100%;
        min-height: 8;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0 1;
    }
    HomeNavCard:focus {
        background: #0f172a;
    }
    HomeNavCard:hover {
        background: #0d1527;
    }
    """

    def __init__(
        self,
        card_id: str,
        number: str,
        title: str,
        subtitle_lines: List[str],
        top_badge: Optional[str] = None,
        bottom_badge: Optional[str] = None,
        graphic_type: str = "ecg",
        device_count: int = 0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, label=title, id=card_id, **kwargs)
        self.card_number = number
        self.card_title = title
        self.subtitle_lines = subtitle_lines
        self.top_badge = top_badge
        self.bottom_badge = bottom_badge
        self.graphic_type = graphic_type
        self.device_count = device_count

    def render(self) -> Panel:
        default_w = 55 if self.graphic_type in ["inventory", "audit"] else 38
        width = self.size.width if self.size.width > 20 else default_w
        inner_width = max(24, width - 4)

        is_active = self.has_focus or self.has_pseudo_class("hover")
        border_color = "#00e5ff" if is_active else "#00b4d8"

        t = Text()
        # 1. Title line: [1] TROUBLESHOOTING
        t.append(f"[{self.card_number}] ", style="bold #fbbf24")
        t.append(f"{self.card_title}\n", style="bold white")

        # 2. Subtitle lines
        for line in self.subtitle_lines:
            t.append(f"{line}\n", style="#cbd5e1")
        t.append("\n")

        # 3. Bottom indicators & graphics
        if self.graphic_type == "ecg":
            # Card 1: ● ACTIVO ... ___/|¯\_
            left_part = "● ACTIVO"
            right_part = "___/|¯\\_"
            spaces = max(2, inner_width - len(left_part) - len(right_part))
            t.append(left_part, style="bold #22c55e")
            t.append(" " * spaces)
            t.append(right_part, style="bold #f43f5e")

        elif self.graphic_type == "gear_sliders":
            # Card 2: ● LISTO ... ⚙ ⊸
            left_part = "● LISTO"
            right_part = "⚙ ⊸"
            spaces = max(2, inner_width - len(left_part) - 4)
            t.append(left_part, style="bold #22c55e")
            t.append(" " * spaces)
            t.append(right_part, style="bold #00e5ff")

        elif self.graphic_type == "terminal_box":
            # Card 3: ● LISTO ... [>_]
            left_part = "● LISTO"
            right_part = "[>_]"
            spaces = max(2, inner_width - len(left_part) - len(right_part))
            t.append(left_part, style="bold #22c55e")
            t.append(" " * spaces)
            t.append(right_part, style="bold #00e5ff")

        elif self.graphic_type == "inventory":
            # Card 4: [████████████████░░░░] 15/15 ... (((•)))
            #         ░░░░░░░░░░░░░░░░░░░░░░        [ ... ]
            count_str = f"{self.device_count}/{self.device_count}" if self.device_count > 0 else "0/0"
            bar = "[████████████████░░░░] " + count_str
            wifi_top = "(((•)))"
            spaces_1 = max(4, inner_width - len(bar) - len(wifi_top))
            t.append(bar, style="bold #00e5ff")
            t.append(" " * spaces_1)
            t.append(wifi_top + "\n", style="bold #38bdf8")

            hatch = "░" * 22
            wifi_bot = "[ ... ]"
            spaces_2 = max(4, inner_width - len(hatch) - len(wifi_bot))
            t.append(hatch, style="dim #00e5ff")
            t.append(" " * spaces_2)
            t.append(wifi_bot, style="bold #00e5ff")

        elif self.graphic_type == "audit":
            # Card 5: |===| ==================== |:::::
            col_bar_width = max(10, inner_width - 18)
            equals = "=" * col_bar_width
            t.append(f"|===| {equals} |:::::\n", style="#00b4d8")
            t.append(f"|===| {equals} |:::::\n", style="#0077b6")
            t.append(f"|===| {equals} \\:::::", style="#023e8a")

        top_title = f"[bold #38bdf8]● {self.top_badge}[/]" if self.top_badge else None

        return Panel(
            t,
            title=top_title,
            title_align="right",
            border_style=border_color,
            box=box.ROUNDED,
            padding=(0, 1),
        )


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
        devices = db.list_devices()

        with Vertical(id="home-container"):
            # Minimalist Sci-Fi ASCII Banner
            yield BannerWidget(id="home-banner")

            # Operational Status Card
            yield Static(id="home-status-card")

            # 5 Action Cards in Cyberpunk Mission Control Layout
            with Vertical(id="home-cards-container"):
                # Top Row: 3 Operational Pillars
                with Horizontal(id="home-cards-row-top"):
                    yield HomeNavCard(
                        card_id="btn-nav-troubleshooting",
                        number="1",
                        title="TROUBLESHOOTING",
                        subtitle_lines=["Diagnóstico autónomo y análisis", "de causa raíz"],
                        top_badge="ACTIVO",
                        bottom_badge="ACTIVO",
                        graphic_type="ecg",
                        classes="home-nav-card card-troubleshooting",
                    )
                    yield HomeNavCard(
                        card_id="btn-nav-configuration",
                        number="2",
                        title="CONFIGURACION",
                        subtitle_lines=["Aprovisionamiento de BGP, OSPF,", "VLANs y ACLs"],
                        top_badge="LISTO",
                        bottom_badge="LISTO",
                        graphic_type="gear_sliders",
                        classes="home-nav-card card-configuration",
                    )
                    yield HomeNavCard(
                        card_id="btn-nav-automation",
                        number="3",
                        title="AUTOMATIZACION",
                        subtitle_lines=["Editor Jinja2, validación", "sintáctica y despliegue"],
                        top_badge="LISTO",
                        bottom_badge="LISTO",
                        graphic_type="terminal_box",
                        classes="home-nav-card card-automation",
                    )

                # Bottom Row: Management & Audit
                with Horizontal(id="home-cards-row-bottom"):
                    yield HomeNavCard(
                        card_id="btn-nav-inventory",
                        number="4",
                        title="INVENTARIO DE EQUIPOS",
                        subtitle_lines=["Catálogo de routers y prueba de", "conectividad"],
                        graphic_type="inventory",
                        device_count=len(devices),
                        classes="home-nav-card card-inventory",
                    )
                    yield HomeNavCard(
                        card_id="btn-nav-audit",
                        number="5",
                        title="REGISTRO DE AUDITORIA",
                        subtitle_lines=["Bitácora de cambios, eventos y", "rollbacks"],
                        graphic_type="audit",
                        classes="home-nav-card card-audit",
                    )

    def on_mount(self) -> None:
        self.update_status_card()

    def update_status_card(self) -> None:
        """Render the system status summary panel."""
        card = self.query_one("#home-status-card", Static)
        provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
        model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:14b"
        devices = db.list_devices()
        auto_approve = db.get_setting("auto_approve") == "true" or settings.auto_approve

        # Truncate model name if long to keep on 1 line
        if len(model) > 16:
            model_display = f"{model[:6]}..{model[-4:]}"
        else:
            model_display = model

        hitl_status = (
            "[bold #4ade80]ACTIVO (Confirmación Requerida)[/]"
            if not auto_approve
            else "[bold #ef4444]DESACTIVADO (Auto-Approve ON)[/]"
        )

        status_text = Text.from_markup(
            f"[bold #00e5ff]ESTADO DEL SISTEMA:[/] IA: [bold #bc8cff]{provider.upper()}[/] "
            f"([#94a3b8]{model_display}[/]) | "
            f"Inventario: [bold #00e5ff]{len(devices)} equipos[/] | "
            f"HitL: {hitl_status}\n"
            f"[#64748b]Atajos:[/] [bold #fbbf24][1-5][/] [#e2e8f0]Seleccionar Módulo[/] | "
            f"[bold #fbbf24][S][/] [#e2e8f0]Ajustes IA[/] | "
            f"[bold #fbbf24][D][/] [#e2e8f0]Nuevo Equipo[/] | "
            f"[bold #fbbf24][Q][/] [#e2e8f0]Salir[/]"
        )

        panel = Panel(
            status_text,
            title="PANEL DE CONTROL OPERACIONAL",
            border_style="#00b4d8",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        card.update(panel)

        try:
            card_inv = self.query_one("#btn-nav-inventory", HomeNavCard)
            card_inv.device_count = len(devices)
            card_inv.refresh()
        except Exception:
            pass

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
