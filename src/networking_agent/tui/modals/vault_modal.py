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
        ("Google Gemini (Cloud)", "gemini"),
        ("OpenAI (Cloud)", "openai"),
        ("Anthropic Claude (Cloud)", "anthropic"),
    ]

    PROVIDER_METADATA = {
        "ollama": {
            "label": "Servidor Ollama Host / URL (Local):",
            "placeholder": "http://localhost:11434",
            "default_model": "qwen2.5-coder:14b",
            "is_secret": False,
            "help": "Inferencia privada y soberana local (no requiere API key en la nube).",
            "setting_key": "ollama_host",
            "default_val": "http://localhost:11434",
        },
        "gemini": {
            "label": "Google Gemini API Key (Cifrado Fernet):",
            "placeholder": "AIzaSy...",
            "default_model": "gemini-2.5-flash",
            "is_secret": True,
            "help": "Google Cloud AI API (cifrado simétrico local AES-128 con Fernet).",
            "setting_key": "gemini_api_key",
            "default_val": "",
        },
        "openai": {
            "label": "OpenAI API Key (Cifrado Fernet):",
            "placeholder": "sk-proj-...",
            "default_model": "gpt-4o",
            "is_secret": True,
            "help": "OpenAI Platform API (cifrado simétrico local AES-128 con Fernet).",
            "setting_key": "openai_api_key",
            "default_val": "",
        },
        "anthropic": {
            "label": "Anthropic Claude API Key (Cifrado Fernet):",
            "placeholder": "sk-ant-...",
            "default_model": "claude-3-5-sonnet-latest",
            "is_secret": True,
            "help": "Anthropic Claude API (cifrado simétrico local AES-128 con Fernet).",
            "setting_key": "anthropic_api_key",
            "default_val": "",
        },
    }

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("CONFIGURACION DE INTELIGENCIA ARTIFICIAL", classes="modal-title")

            current_provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
            current_model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:14b"
            meta = self.PROVIDER_METADATA.get(current_provider, self.PROVIDER_METADATA["ollama"])

            with Horizontal(classes="modal-row"):
                with Vertical(classes="modal-col"):
                    yield Label("Proveedor de IA:")
                    yield Select(
                        self.PROVIDER_CHOICES,
                        value=current_provider,
                        id="select-provider",
                        allow_blank=False,
                    )
                with Vertical(classes="modal-col"):
                    yield Label("Modelo LLM:")
                    yield Input(value=current_model, id="input-model")

            # Dynamic Credential / Host section
            yield Label(meta["label"], id="lbl-credential")
            if meta["is_secret"]:
                raw_val = vault.decrypt(db.get_setting(meta["setting_key"])) or ""
            else:
                raw_val = db.get_setting(meta["setting_key"]) or meta["default_val"]

            yield Input(
                value=raw_val,
                password=meta["is_secret"],
                placeholder=meta["placeholder"],
                id="input-api-key",
            )
            yield Label(meta["help"], id="lbl-provider-help", classes="provider-help-text")

            current_auto = db.get_setting("auto_approve") == "true" or settings.auto_approve
            yield Checkbox(
                "Modo Auto-Approve (Desactiva confirmacion humana HitL)",
                value=current_auto,
                id="chk-auto",
            )

            with Horizontal(classes="modal-actions"):
                yield Button("Guardar Cambios", id="btn-save-vault", variant="primary")
                yield Button("Cerrar", id="btn-cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Dynamically update input labels, password masking, and models when provider changes."""
        if event.select.id == "select-provider" and event.value != Select.BLANK:
            self._update_provider_fields(str(event.value))

    def _update_provider_fields(self, provider: str) -> None:
        meta = self.PROVIDER_METADATA.get(provider, self.PROVIDER_METADATA["ollama"])
        lbl_cred = self.query_one("#lbl-credential", Label)
        inp_cred = self.query_one("#input-api-key", Input)
        lbl_help = self.query_one("#lbl-provider-help", Label)
        inp_model = self.query_one("#input-model", Input)

        lbl_cred.update(meta["label"])
        lbl_help.update(meta["help"])
        inp_cred.placeholder = meta["placeholder"]
        inp_cred.password = meta["is_secret"]

        if meta["is_secret"]:
            stored = vault.decrypt(db.get_setting(meta["setting_key"])) or ""
        else:
            stored = db.get_setting(meta["setting_key"]) or meta["default_val"]
        inp_cred.value = stored

        # Switch to recommended default model if empty or currently at a default of another provider
        curr_m = inp_model.value.strip()
        all_defaults = {m["default_model"] for m in self.PROVIDER_METADATA.values()}
        if not curr_m or curr_m in all_defaults:
            inp_model.value = meta["default_model"]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-vault":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        provider = str(self.query_one("#select-provider", Select).value)
        model = self.query_one("#input-model", Input).value.strip()
        cred_val = self.query_one("#input-api-key", Input).value.strip()
        auto_approve = self.query_one("#chk-auto", Checkbox).value

        meta = self.PROVIDER_METADATA.get(provider, self.PROVIDER_METADATA["ollama"])

        # Persist provider and model
        db.set_setting("ai_provider", provider)
        db.set_setting("ai_model", model)

        # Persist credential or host
        if meta["is_secret"]:
            if cred_val:
                db.set_setting(meta["setting_key"], vault.encrypt(cred_val))
            if provider == "gemini" and cred_val:
                db.set_setting("gemini_api_key", vault.encrypt(cred_val))
        else:
            db.set_setting(meta["setting_key"], cred_val or meta["default_val"])

        db.set_setting("auto_approve", "true" if auto_approve else "false")

        self.dismiss(
            {
                "provider": provider,
                "model": model,
                "api_key": cred_val,
                "auto_approve": str(auto_approve).lower(),
            }
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
