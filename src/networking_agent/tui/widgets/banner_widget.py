"""Typography banner widget for the NetworkingAgent Textual TUI."""

from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

ASCII_BANNER = r"""  _   _      _                      _     _               _                    _   
 | \ | | ___| |___      _____  _ __| | __(_)_ __   __ _  / \   __ _  ___ _ __ | |_ 
 |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ /| | '_ \ / _` |/ _ \ / _` |/ _ \ '_ \| __|
 | |\  |  __/ |_ \ V  V / (_) | |  |   < | | | | | (_| / ___ \ (_| |  __/ | | | |_ 
 |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\|_|_| |_|\__, /_/   \_\__, |\___|_| |_|\__|
                                                   |___/        |___/                """

BANNER_TAGLINE = "Enterprise Autonomous Closed-Loop Network Engineering Agent"
BANNER_SUBS = "Cisco | Juniper | MikroTik  --  Ollama | Gemini | OpenAI | Claude"


class BannerWidget(Static):
    """Renders a clean, minimalist ASCII banner with version metadata."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin-bottom: 1;
        width: 100%;
    }
    """

    def render(self) -> Panel:
        banner_text = Text(no_wrap=True)
        banner_text.append(ASCII_BANNER + "\n", style="bold cyan")
        banner_text.append(f"{BANNER_TAGLINE}\n", style="bold white")
        banner_text.append(BANNER_SUBS, style="dim white")

        return Panel(
            Align.center(banner_text),
            border_style="cyan",
            padding=(0, 1),
        )
