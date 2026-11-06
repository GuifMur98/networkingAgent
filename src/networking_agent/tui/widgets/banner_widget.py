"""ASCII Art typography banner widget for the NetworkingAgent Textual TUI."""

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

COMPACT_BANNER = r""" _   _      _                      _               _   
| \ | | ___| |___      _____  _ __| | __  /\   ___| |_ 
|  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / /  \ / _ \ __|
| |\  |  __/ |_ \ V  V / (_) | |  |   < / /\ \  __/ |_ 
|_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_/_/  \_\___|\__|"""


class BannerWidget(Static):
    """Renders the prominent ASCII art logo and enterprise tagline."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin-bottom: 1;
        width: 100%;
    }
    """

    def render(self) -> Panel:
        width = self.size.width or 100
        raw_art = ASCII_BANNER if width >= 90 else COMPACT_BANNER

        banner_text = Text()
        banner_text.append(raw_art + "\n\n", style="bold #00e5ff")
        banner_text.append("Enterprise Autonomous Closed-Loop Network Agent\n", style="bold white")
        banner_text.append("Cisco • Juniper • MikroTik  |  Ollama • Gemini • OpenAI • Claude", style="dim cyan")

        return Panel(
            Align.center(banner_text),
            border_style="#00e5ff",
            padding=(0, 1),
        )
