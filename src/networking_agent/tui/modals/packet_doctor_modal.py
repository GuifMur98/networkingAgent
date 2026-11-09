"""AI Packet Doctor diagnosis modal screen."""

from rich.markdown import Markdown
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class PacketDoctorModal(ModalScreen[None]):
    """Modal displaying the AI Packet Doctor statistical and root-cause analysis."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cerrar", show=True),
        Binding("enter", "dismiss_modal", "Aceptar", show=True),
    ]

    def __init__(self, report_markdown: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_markdown = report_markdown

    def compose(self) -> ComposeResult:
        with Vertical(id="packet-doctor-dialog", classes="modal-dialog-box"):
            with VerticalScroll(id="packet-doctor-scroll"):
                yield Static(Markdown(self.report_markdown), id="packet-doctor-content")
            yield Button("Cerrar Informe (Esc / Enter)", id="btn-close-doctor", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-close-doctor":
            self.dismiss(None)

    def action_dismiss_modal(self):
        self.dismiss(None)
