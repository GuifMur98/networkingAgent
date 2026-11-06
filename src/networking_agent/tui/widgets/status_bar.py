"""Header and status indicator widget for NetworkingAgent TUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static


class TopStatusBar(Static):
    """Top bar displaying brand, active brain model, inventory statistics, and guardrail mode."""

    DEFAULT_CSS = """
    TopStatusBar {
        height: 3;
        dock: top;
        background: #182230;
        border-bottom: heavy #00e5ff;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        brain_info: str = "Ollama: qwen2.5-coder:7b",
        device_count: int = 0,
        auto_approve: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.brain_info = brain_info
        self.device_count = device_count
        self.auto_approve = auto_approve

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-bar-inner"):
            yield Label("⚡ NetworkingAgent Enterprise AI", id="top-title")
            with Horizontal(id="top-badges"):
                yield Label(f"🧠 Brain: {self.brain_info}", id="badge-brain", classes="status-badge badge-brain")
                yield Label(f"🖥️ Devices: {self.device_count}", id="badge-devs", classes="status-badge badge-device")
                hitl_txt = "🛡️ HitL: Active" if not self.auto_approve else "⚠️ Auto-Approve: ON"
                yield Label(hitl_txt, id="badge-hitl", classes="status-badge badge-hitl")

    def update_brain(self, brain_info: str) -> None:
        self.brain_info = brain_info
        badge = self.query_one("#badge-brain", Label)
        badge.update(f"🧠 Brain: {self.brain_info}")

    def update_device_count(self, count: int) -> None:
        self.device_count = count
        badge = self.query_one("#badge-devs", Label)
        badge.update(f"🖥️ Devices: {self.device_count}")

    def update_hitl_mode(self, auto_approve: bool) -> None:
        self.auto_approve = auto_approve
        badge = self.query_one("#badge-hitl", Label)
        hitl_txt = "🛡️ HitL: Active" if not self.auto_approve else "⚠️ Auto-Approve: ON"
        badge.update(hitl_txt)
