"""Typography banner widget for the NetworkingAgent Textual TUI."""

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

BANNER_TAGLINE = "Enterprise Autonomous Closed-Loop Network Engineering Agent"

# 3D block gradient title: NETWORKING AGENT
L1 = "█▄   █ █▀▀▀█ ▀█▀ █     █ ▄▀▀▀▄ █▀▀▀█ █ ▄▀ █ █▄   █ ▄▀▀▀█   ▄▀▀▀▄ ▄▀▀▀█ █▀▀▀█ █▄   █ ▀█▀"
L2 = "██▄  █ █▄▄▄    █  █  █  █ █   █ █▄▄▄▀ █▀▄  █ ██▄  █ █ ▄▄▄   █▀▀▀█ █ ▄▄▄ █▄▄▄   ██▄  █  █ "
L3 = "█ ▀▄ █ █       █  █ █ █ █ █   █ █   █ █  █ █ █ ▀▄ █ █   █   █   █ █   █ █      █ ▀▄ █  █ "
L4 = "█   ██ █▄▄▄█   █   █   █   ▀▄▄▀ █   █ █   █ █ █   ██  ▀▄▄▀   █   █  ▀▄▄▀ █▄▄▄█ █   ██  █ "

DOT_L1 = "  . " + (" " * 94) + "o  \n"
DOT_L2 = "  - " + (" " * 94) + "-  \n"
DOT_L3 = "  o " + (" " * 94) + ".  \n"
GLYPH_MID = "(-; , _" + (" " * 86) + "_ , ;-)\n"


class BannerWidget(Static):
    """Renders a futuristic Cyberpunk / Mission Control ASCII banner with sci-fi frame."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin-bottom: 1;
        width: 100%;
    }
    """

    def render(self) -> Panel:
        t = Text()

        # Top sci-fi glyphs line
        t.append(DOT_L1, style="dim #00e5ff")
        t.append(DOT_L2, style="dim #00e5ff")
        t.append(DOT_L3, style="dim #00e5ff")

        # 3D block gradient title
        t.append(f"          {L1}          \n", style="bold #a5f3fc")
        t.append(f"          {L2}           \n", style="bold #38bdf8")
        t.append(f"          {L3}           \n", style="bold #0284c7")
        t.append(f"          {L4}           \n", style="bold #0369a1")

        # Side brackets decoration line
        t.append(GLYPH_MID, style="dim #00e5ff")

        # Tagline and vendor subtitles
        t.append(f"                   {BANNER_TAGLINE}                        \n", style="bold #f59e0b")
        t.append("                   Cisco | Juniper | MikroTik  --  ", style="#94a3b8")
        t.append("Ollama", style="bold #38bdf8")
        t.append(" | Gemini | OpenAI | Claude                    \n", style="#64748b")

        box_title = "[bold #00e5ff][--" + (" " * 70) + "[--]][/]"
        box_sub = "[bold #00e5ff][--]" + (" " * 70) + "[--]][/]"

        return Panel(
            Align.center(t),
            title=box_title,
            subtitle=box_sub,
            border_style="#00b4d8",
            box=box.ROUNDED,
            padding=(0, 0),
        )
