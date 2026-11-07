"""Typography banner widget for the NetworkingAgent Textual TUI."""

from rich.align import Align
from rich.text import Text
from textual.widgets import Static

BANNER_TAGLINE = "Enterprise Autonomous Closed-Loop Network Engineering Agent"

# Solid 81-column block font: NETWORKING AGENT
R1 = "█   █ ████ █████ █   █ ████ ████ █  █ ███ █   █ ████   ████ ████ ████ █   █ █████"
R2 = "██  █ █      █   █ █ █ █  █ █  █ █ █   █  ██  █ █      █  █ █    █    ██  █   █  "
R3 = "█ █ █ ███    █   █ █ █ █  █ ████ ██    █  █ █ █ █ ██   ████ █ ██ ███  █ █ █   █  "
R4 = "█  ██ █      █   ██ ██ █  █ █ █  █ █   █  █  ██ █  █   █  █ █  █ █    █  ██   █  "
R5 = "█   █ ████   █   █   █ ████ █  █ █  █ ███ █   █ ████   █  █ ████ ████ █   █   █  "

W = 96
DASH_TOP = "─" * 89  # 96 - 7
DASH_BOT = "─" * 88  # 96 - 8
SPACES_DOT = " " * 86
SPACES_MID = " " * 82

VENDORS_PREFIX = "Cisco | Juniper | MikroTik  --  "
VENDORS_OLLAMA = "Ollama"
VENDORS_SUFFIX = " | Gemini | OpenAI | Claude"


class BannerWidget(Static):
    """Renders a futuristic Cyberpunk / Mission Control ASCII banner with sci-fi frame."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin-bottom: 1;
        width: 100%;
    }
    """

    def render(self) -> Align:
        t = Text()

        # 1. Top border: [--──────...──────[--]
        t.append("[--", style="bold #00e5ff")
        t.append(DASH_TOP, style="dim #00e5ff")
        t.append("[--]\n", style="bold #00e5ff")

        # 2-4. Antenna / radar dot lines (. - o ... o - .)
        dot_pairs = [(". ", "o  "), ("- ", "-  "), ("o ", ".  ")]
        for d_l, d_r in dot_pairs:
            t.append("│  ", style="dim #00e5ff")
            t.append(d_l, style="dim #00e5ff")
            t.append(SPACES_DOT)
            t.append(d_r, style="dim #00e5ff")
            t.append("│\n", style="dim #00e5ff")

        # 5-9. Solid block 5-row gradient title (centered in 96 cols: 6 spaces left, 7 right)
        rows = [
            (R1, "bold #a5f3fc"),
            (R2, "bold #67e8f9"),
            (R3, "bold #38bdf8"),
            (R4, "bold #0284c7"),
            (R5, "bold #0369a1"),
        ]
        for r, style in rows:
            t.append("│      ", style="dim #00e5ff")
            t.append(r, style=style)
            t.append("       │\n", style="dim #00e5ff")

        # 10. Mid glyphs: (-; , _ ... _ , ;-)
        t.append("(-; , _", style="dim #00e5ff")
        t.append(SPACES_MID)
        t.append("_ , ;-)\n", style="dim #00e5ff")

        # 11. Tagline: Enterprise Autonomous Closed-Loop Network Engineering Agent
        t.append("│" + (" " * 17), style="dim #00e5ff")
        t.append(BANNER_TAGLINE, style="bold #f59e0b")
        t.append((" " * 18) + "│\n", style="dim #00e5ff")

        # 12. Multi-vendor & Brain list
        t.append("│" + (" " * 14), style="dim #00e5ff")
        t.append(VENDORS_PREFIX, style="#94a3b8")
        t.append(VENDORS_OLLAMA, style="bold #38bdf8")
        t.append(VENDORS_SUFFIX, style="#64748b")
        t.append((" " * 15) + "│\n", style="dim #00e5ff")

        # 13. Bottom border: [--]──────...──────[--]
        t.append("[--]", style="bold #00e5ff")
        t.append(DASH_BOT, style="dim #00e5ff")
        t.append("[--]\n", style="bold #00e5ff")

        return Align.center(t)
