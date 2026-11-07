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

VENDORS_PREFIX = "Cisco | Juniper | MikroTik  --  "
VENDORS_OLLAMA = "Ollama"
VENDORS_SUFFIX = " | Gemini | OpenAI | Claude"
VENDORS_LEN = len(VENDORS_PREFIX) + len(VENDORS_OLLAMA) + len(VENDORS_SUFFIX)  # 65


class BannerWidget(Static):
    """Renders a futuristic Cyberpunk / Mission Control ASCII banner with dynamic sci-fi frame."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin-bottom: 1;
        width: 100%;
    }
    """

    def on_resize(self) -> None:
        self.refresh()

    def render(self):
        # Dynamically adapt frame width to match container / terminal width (min 96 cols)
        w = max(96, self.size.width if self.size.width > 20 else 120)

        t = Text(no_wrap=True)

        # 1. Top border: [--──────...──────[--]
        t.append("[--", style="bold #00e5ff")
        t.append("─" * (w - 7), style="dim #00e5ff")
        t.append("[--]", style="bold #00e5ff")

        # 2-4. Antenna / radar dot lines (. - o ... o - .)
        dot_pairs = [(".", "o"), ("-", "-"), ("o", ".")]
        dot_spaces = " " * (w - 10)
        for d_l, d_r in dot_pairs:
            t.append("\n")
            t.append("│  ", style="dim #00e5ff")
            t.append(d_l + " ", style="dim #00e5ff")
            t.append(dot_spaces)
            t.append(" " + d_r, style="dim #00e5ff")
            t.append("  │", style="dim #00e5ff")

        # 5-9. Solid block 5-row gradient title (centered inside width w)
        title_pad_total = w - 2 - 81
        pad_left = " " * (title_pad_total // 2)
        pad_right = " " * (title_pad_total - (title_pad_total // 2))

        rows = [
            (R1, "bold #a5f3fc"),
            (R2, "bold #67e8f9"),
            (R3, "bold #38bdf8"),
            (R4, "bold #0284c7"),
            (R5, "bold #0369a1"),
        ]
        for r, style in rows:
            t.append("\n")
            t.append("│" + pad_left, style="dim #00e5ff")
            t.append(r, style=style)
            t.append(pad_right + "│", style="dim #00e5ff")

        # 10. Mid glyphs: (-; , _ ... _ , ;-)
        mid_spaces = " " * (w - 14)
        t.append("\n")
        t.append("(-; , _", style="dim #00e5ff")
        t.append(mid_spaces)
        t.append("_ , ;-)", style="dim #00e5ff")

        # 11. Tagline: Enterprise Autonomous Closed-Loop Network Engineering Agent
        tag_pad_total = w - 2 - len(BANNER_TAGLINE)
        tag_left = " " * (tag_pad_total // 2)
        tag_right = " " * (tag_pad_total - (tag_pad_total // 2))
        t.append("\n")
        t.append("│" + tag_left, style="dim #00e5ff")
        t.append(BANNER_TAGLINE, style="bold #f59e0b")
        t.append(tag_right + "│", style="dim #00e5ff")

        # 12. Multi-vendor & Brain list
        ven_pad_total = w - 2 - VENDORS_LEN
        ven_left = " " * (ven_pad_total // 2)
        ven_right = " " * (ven_pad_total - (ven_pad_total // 2))
        t.append("\n")
        t.append("│" + ven_left, style="dim #00e5ff")
        t.append(VENDORS_PREFIX, style="#94a3b8")
        t.append(VENDORS_OLLAMA, style="bold #38bdf8")
        t.append(VENDORS_SUFFIX, style="#64748b")
        t.append(ven_right + "│", style="dim #00e5ff")

        # 13. Bottom border: [--]──────...──────[--]
        t.append("\n")
        t.append("[--]", style="bold #00e5ff")
        t.append("─" * (w - 8), style="dim #00e5ff")
        t.append("[--]", style="bold #00e5ff")

        if self.size.width > w:
            return Align.center(t)
        return t
