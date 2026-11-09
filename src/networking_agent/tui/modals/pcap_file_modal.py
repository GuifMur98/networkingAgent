"""Modals for saving and loading PCAP capture files with custom paths."""

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class SavePcapModal(ModalScreen[Optional[Path]]):
    """Modal dialog prompting the engineer for destination path to save .pcap file."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    def __init__(self, default_path: str = "captura_red.pcap", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_path = default_path

    def compose(self) -> ComposeResult:
        with Vertical(id="pcap-save-dialog", classes="modal-dialog-box"):
            yield Label("GUARDAR CAPTURA EN ARCHIVO PCAP", id="pcap-dialog-title")
            yield Label(
                "Ingrese la ruta o nombre del archivo .pcap donde desea guardar las tramas:",
                classes="modal-desc",
            )
            yield Input(value=self.default_path, id="input-pcap-path")
            with Horizontal(classes="modal-btn-row"):
                yield Button("Guardar [Enter]", id="btn-confirm-save", variant="primary")
                yield Button("Cancelar [Esc]", id="btn-cancel-save", variant="default")

    def on_mount(self):
        self.query_one("#input-pcap-path", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        self._submit()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-confirm-save":
            self._submit()
        elif event.button.id == "btn-cancel-save":
            self.dismiss(None)

    def _submit(self):
        val = self.query_one("#input-pcap-path", Input).value.strip()
        if val:
            p = Path(val)
            if not p.suffix:
                p = p.with_suffix(".pcap")
            self.dismiss(p)
        else:
            self.dismiss(Path(self.default_path))

    def action_cancel(self):
        self.dismiss(None)


class LoadPcapModal(ModalScreen[Optional[Path]]):
    """Modal dialog prompting the engineer for the .pcap file path to load."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    def __init__(self, default_path: str = "captura_red.pcap", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_path = default_path

    def compose(self) -> ComposeResult:
        with Vertical(id="pcap-load-dialog", classes="modal-dialog-box"):
            yield Label("CARGAR ARCHIVO DE CAPTURA PCAP", id="pcap-dialog-title")
            yield Label("Ingrese la ruta del archivo .pcap que desea importar para análisis:", classes="modal-desc")
            yield Input(value=self.default_path, id="input-load-pcap-path")
            with Horizontal(classes="modal-btn-row"):
                yield Button("Cargar [Enter]", id="btn-confirm-load", variant="primary")
                yield Button("Cancelar [Esc]", id="btn-cancel-load", variant="default")

    def on_mount(self):
        self.query_one("#input-load-pcap-path", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        self._submit()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-confirm-load":
            self._submit()
        elif event.button.id == "btn-cancel-load":
            self.dismiss(None)

    def _submit(self):
        val = self.query_one("#input-load-pcap-path", Input).value.strip()
        if val:
            self.dismiss(Path(val))
        else:
            self.dismiss(Path(self.default_path))

    def action_cancel(self):
        self.dismiss(None)
