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
        background: #161b22;
        border-bottom: heavy #388bfd;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        brain_info: str = "ollama:qwen2.5-coder:7b",
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

            with Horizontal(id="top-badges"):
                yield Label(f"BRAIN: {self.brain_info}", id="badge-brain", classes="status-badge badge-brain")
                yield Label(f"EQUIPOS: {self.device_count}", id="badge-devs", classes="status-badge badge-device")
                hitl_txt = "HITL: ACTIVO" if not self.auto_approve else "AUTO-APPROVE: ON"
                yield Label(hitl_txt, id="badge-hitl", classes="status-badge badge-hitl")

    def update_brain(self, brain_info: str) -> None:
        self.brain_info = brain_info
        badge = self.query_one("#badge-brain", Label)
        badge.update(f"BRAIN: {self.brain_info}")

    def update_device_count(self, count: int) -> None:
        self.device_count = count
        badge = self.query_one("#badge-devs", Label)
        badge.update(f"EQUIPOS: {self.device_count}")

    def update_hitl_mode(self, auto_approve: bool) -> None:
        self.auto_approve = auto_approve
        badge = self.query_one("#badge-hitl", Label)
        hitl_txt = "HITL: ACTIVO" if not self.auto_approve else "AUTO-APPROVE: ON"
        badge.update(hitl_txt)
