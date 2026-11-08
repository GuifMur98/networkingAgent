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


def _clean_rich_color(color_val: str | None, fallback: str) -> str:
    """Sanitize color names for Rich styling, handling Textual ANSI theme values."""
    if not color_val:
        return fallback
    val = str(color_val).strip()
    if "ansi_" in val:
        val = val.replace("ansi_", "")
    if val in ("default", "none", "None", ""):
        return fallback
    return val


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

        # Dynamic theme palette
        theme = getattr(self.app, "current_theme", None)
        is_dark = getattr(theme, "dark", True) if theme else True
        primary = _clean_rich_color(getattr(theme, "primary", None), "#00e5ff" if is_dark else "#0369a1")
        secondary = _clean_rich_color(getattr(theme, "secondary", None), "#00b4d8" if is_dark else "#475569")
        accent = _clean_rich_color(getattr(theme, "accent", None), "#f59e0b" if is_dark else "#d97706")
        fg_dim = "#94a3b8" if is_dark else "#64748b"
        frame_border = f"bold {primary}" if is_dark else "bold #0369a1"
        frame_dim = f"dim {primary}" if is_dark else "dim #94a3b8"

        t = Text(no_wrap=True)

        # 1. Top border: [--]──────...──────[--]
        t.append("[--]", style=frame_border)
        t.append("─" * (w - 8), style=frame_dim)
        t.append("[--]", style=frame_border)

        # 2-4. Antenna / radar dot lines (. - o ... o - .)
        dot_pairs = [(".", "o"), ("-", "-"), ("o", ".")]
        dot_spaces = " " * (w - 10)
        for d_l, d_r in dot_pairs:
            t.append("\n")
            t.append("│  ", style=frame_dim)
            t.append(d_l + " ", style=frame_dim)
            t.append(dot_spaces)
            t.append(" " + d_r, style=frame_dim)
            t.append("  │", style=frame_dim)

        # 5-9. Solid block 5-row gradient title (centered inside width w)
        title_pad_total = w - 2 - 81
        pad_left = " " * (title_pad_total // 2)
        pad_right = " " * (title_pad_total - (title_pad_total // 2))

        if is_dark:
            rows = [
                (R1, "bold #a5f3fc"),
                (R2, "bold #67e8f9"),
                (R3, "bold #38bdf8"),
                (R4, "bold #0284c7"),
                (R5, "bold #0369a1"),
            ]
        else:
            rows = [
                (R1, "bold #0369a1"),
                (R2, "bold #0284c7"),
                (R3, "bold #0f766e"),
                (R4, "bold #0369a1"),
                (R5, "bold #1e293b"),
            ]

        for r, style in rows:
            t.append("\n")
            t.append("│" + pad_left, style=frame_dim)
            t.append(r, style=style)
            t.append(pad_right + "│", style=frame_dim)

        # 10. Mid glyphs: (-; , _ ... _ , ;-)
        mid_spaces = " " * (w - 14)
        t.append("\n")
        t.append("(-; , _", style=frame_dim)
        t.append(mid_spaces)
        t.append("_ , ;-)", style=frame_dim)

        # 11. Tagline: Enterprise Autonomous Closed-Loop Network Engineering Agent
        tag_pad_total = w - 2 - len(BANNER_TAGLINE)
        tag_left = " " * (tag_pad_total // 2)
        tag_right = " " * (tag_pad_total - (tag_pad_total // 2))
        t.append("\n")
        t.append("│" + tag_left, style=frame_dim)
        t.append(BANNER_TAGLINE, style=f"bold {accent}")
        t.append(tag_right + "│", style=frame_dim)

        # 12. Multi-vendor & Brain list
        ven_pad_total = w - 2 - VENDORS_LEN
        ven_left = " " * (ven_pad_total // 2)
        ven_right = " " * (ven_pad_total - (ven_pad_total // 2))
        t.append("\n")
        t.append("│" + ven_left, style=frame_dim)
        t.append(VENDORS_PREFIX, style=fg_dim)
        t.append(VENDORS_OLLAMA, style=f"bold {secondary}")
        t.append(VENDORS_SUFFIX, style=fg_dim)
        t.append(ven_right + "│", style=frame_dim)

        # 13. Bottom border: [--]──────...──────[--]
        t.append("\n")
        t.append("[--]", style=frame_border)
        t.append("─" * (w - 8), style=frame_dim)
        t.append("[--]", style=frame_border)

        if self.size.width > w:
            return Align.center(t)
        return t
