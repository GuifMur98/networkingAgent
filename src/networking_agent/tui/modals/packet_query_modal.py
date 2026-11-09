"""Modal for interactive user query input to AI Packet Doctor."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class PacketAIQueryModal(ModalScreen[Optional[str]]):
    """Modal dialog prompting the engineer for the specific query or problem to investigate with AI."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    QUICK_PROMPTS = [
        ("Lentitud y Retransmisiones", "Investigar causas de retransmisiones TCP y lentitud de flujo"),
        ("Fallos DNS", "Detectar errores de resolución DNS NXDOMAIN o respuestas lentas"),
        ("Reseteos RST", "Identificar causas de desconexiones abruptas y banderas RST"),
        ("Auditoría Integral", "Auditoría forense completa de anomalías y estado de protocolos"),
    ]

    def __init__(self, packet_count: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.packet_count = packet_count

    def compose(self) -> ComposeResult:
        with Vertical(id="packet-ai-dialog", classes="modal-dialog-box"):
            yield Label("DIAGNÓSTICO DE TRÁFICO CON INTELIGENCIA ARTIFICIAL", id="packet-ai-title")
            yield Label(
                f"Sesión activa con {self.packet_count} tramas capturadas. "
                "Indique qué problema o comportamiento desea que el cerebro de IA analice:",
                classes="modal-desc",
            )

            yield Label("Consulta u objetivo de investigación:", classes="input-header-label")
            yield Input(
                placeholder="Ej. ¿Por qué caen las conexiones hacia 10.0.0.1? o Analizar retrasos en DNS...",
                id="input-ai-query",
            )

            yield Label("Consultas rápidas recomendadas:", classes="input-sub-label")
            with Horizontal(id="quick-chips-row"):
                for label, _ in self.QUICK_PROMPTS:
                    yield Button(label, id=f"chip-{label.lower().replace(' ', '-')}", classes="quick-chip-btn")

            with Horizontal(classes="modal-btn-row"):
                yield Button("Analizar con IA [Enter]", id="btn-submit-ai-query", variant="primary")
                yield Button("Cancelar [Esc]", id="btn-cancel-ai-query", variant="default")

    def on_mount(self):
        self.query_one("#input-ai-query", Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "btn-submit-ai-query":
            self._submit()
        elif btn_id == "btn-cancel-ai-query":
            self.dismiss(None)
        elif btn_id and btn_id.startswith("chip-"):
            # Find matching prompt
            for label, prompt in self.QUICK_PROMPTS:
                if btn_id == f"chip-{label.lower().replace(' ', '-')}":
                    inp = self.query_one("#input-ai-query", Input)
                    inp.value = prompt
                    self._submit()
                    break

    def on_input_submitted(self, event: Input.Submitted):
        self._submit()

    def _submit(self):
        val = self.query_one("#input-ai-query", Input).value.strip()
        if not val:
            val = "Auditoría forense completa de anomalías de red, retransmisiones y desempeño de protocolos"
        self.dismiss(val)

    def action_cancel(self):
        self.dismiss(None)
