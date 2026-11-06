"""Typography banner widget for the NetworkingAgent Textual TUI."""

from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

ASCII_BANNER = r"""  _   _      _                      _               _   
 | \ | | ___| |___      _____  _ __| | __  /\   ___| |_ 
 |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / /  \ / _ \ __|
 | |\  |  __/ |_ \ V  V / (_) | |  |   < / /\ \  __/ |_ 
 |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_/_/  \_\___|\__|"""

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
        banner_text = Text()
        banner_text.append(ASCII_BANNER + "\n", style="bold cyan")
        banner_text.append(f"{BANNER_TAGLINE}\n", style="bold white")
        banner_text.append(BANNER_SUBS, style="dim white")

        return Panel(
            Align.center(banner_text),
            border_style="cyan",
            padding=(0, 1),
        )
