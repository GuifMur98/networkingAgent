"""Modal screen for AI brain provider, model, and cryptographic settings configuration."""

from typing import Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select

from networking_agent.core.config import settings
from networking_agent.core.crypto import vault
from networking_agent.core.db import db


class VaultModal(ModalScreen[Optional[Dict[str, str]]]):
    """Dialog screen for configuring AI models, API keys, and HitL preferences."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    PROVIDER_CHOICES = [
        ("Ollama (Local / Soberano)", "ollama"),
        ("Google Gemini (Cloud-Native)", "gemini"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-screen"):
            with Vertical(classes="modal-dialog"):
                yield Label("CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL", classes="modal-title")

                current_provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
                yield Label("Proveedor de Inteligencia Artificial:")
                yield Select(
                    self.PROVIDER_CHOICES,
                    value=current_provider,
                    id="select-provider",
                    allow_blank=False,
                )

                current_model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:7b"
                yield Label("Nombre del Modelo LLM:")
                yield Input(value=current_model, id="input-model")

                yield Label("Google Gemini API Key (Cifrado con Fernet):")
                # Mask key preview
                raw_key = vault.decrypt(db.get_setting("gemini_api_key")) or ""
                yield Input(value=raw_key, password=True, id="input-api-key")

                current_auto = db.get_setting("auto_approve") == "true" or settings.auto_approve
                yield Checkbox("Modo Auto-Approve (Desactiva confirmación HitL)", value=current_auto, id="chk-auto")

                with Horizontal(classes="modal-actions"):
                    yield Button("Guardar Cambios", id="btn-save-vault", variant="success")
                    yield Button("Cerrar", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-vault":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        provider = str(self.query_one("#select-provider", Select).value)
        model = self.query_one("#input-model", Input).value.strip()
        api_key = self.query_one("#input-api-key", Input).value.strip()
        auto_approve = self.query_one("#chk-auto", Checkbox).value

        # Persist to database
        db.set_setting("ai_provider", provider)
        db.set_setting("ai_model", model)
        if api_key:
            db.set_setting("gemini_api_key", vault.encrypt(api_key))
        db.set_setting("auto_approve", "true" if auto_approve else "false")

        self.dismiss(
            {
                "provider": provider,
                "model": model,
                "api_key": api_key,
                "auto_approve": str(auto_approve).lower(),
            }
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
