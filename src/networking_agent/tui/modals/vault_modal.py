"""Modal screen for AI brain provider, model, and cryptographic settings configuration."""

import asyncio
from typing import Dict, List, Optional, Set, Tuple

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select

from networking_agent.brains.discovery import (
    discover_provider_models,
    get_cached_ollama_models,
)
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._installed_model_names: Set[str] = set()

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("CONFIGURACION DE INTELIGENCIA ARTIFICIAL", classes="modal-title")

            current_provider = db.get_setting("ai_provider") or settings.ai_provider or "ollama"
            current_model = db.get_setting("ai_model") or settings.ai_model or "qwen2.5-coder:14b"
            meta = self.PROVIDER_METADATA.get(current_provider, self.PROVIDER_METADATA["ollama"])

            # 1. Discover models without blocking the UI thread (allow_network=False)
            initial_choices, initial_val, status_msg = self._build_model_choices(
                current_provider,
                current_model,
                host=db.get_setting("ollama_host") or settings.ollama_host,
                allow_network=False,
            )

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
                    yield Label("Modelos Disponibles:")
                    yield Select(
                        initial_choices,
                        value=initial_val,
                        id="select-model",
                        allow_blank=False,
                    )

            with Horizontal(classes="modal-row"):
                with Vertical(classes="modal-col-large"):
                    yield Label("Modelo LLM Seleccionado / Personalizado:")
                    yield Input(value=current_model, id="input-model", placeholder="ej: qwen3.8:27b, gpt-4o...")
                with Vertical(classes="modal-col-small"):
                    yield Label("Acción:")
                    yield Button("Escanear", id="btn-scan-models")

            yield Label(status_msg, id="lbl-model-status", classes="model-status-text")

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

    def on_mount(self) -> None:
        """Trigger background scan for Ollama models if not already cached."""
        provider = str(self.query_one("#select-provider", Select).value)
        if provider == "ollama":
            host = self.query_one("#input-api-key", Input).value.strip() or None
            # If not already in cache, scan in background thread without freezing UI
            if get_cached_ollama_models(host=host) is None:
                self.run_background_scan(is_manual=False)

    @work(exclusive=True)
    async def run_background_scan(self, is_manual: bool = False) -> None:
        """Scan Ollama models asynchronously in background thread without freezing UI."""
        try:
            btn_scan = self.query_one("#btn-scan-models", Button)
            lbl_status = self.query_one("#lbl-model-status", Label)
            sel_model = self.query_one("#select-model", Select)
            inp_model = self.query_one("#input-model", Input)
            sel_provider = self.query_one("#select-provider", Select)
        except Exception:
            return

        provider = str(sel_provider.value)
        host = self.query_one("#input-api-key", Input).value.strip() or None

        if is_manual:
            btn_scan.disabled = True
            btn_scan.label = "Buscando..."
            lbl_status.update("[bold cyan][>] Consultando modelos en Ollama...[/bold cyan]")

        # Run query asynchronously in worker thread without blocking the UI
        discovered = await asyncio.to_thread(
            discover_provider_models,
            provider,
            host=host,
            force_refresh=is_manual,
            allow_network=True,
        )

        try:
            self._installed_model_names = {m_id for _, m_id in discovered}
            choices, sel_val, status_msg = self._format_choices_and_status(
                provider, inp_model.value.strip(), discovered
            )
            sel_model.set_options(choices)
            if sel_val:
                sel_model.value = sel_val
            lbl_status.update(status_msg)

            if is_manual:
                btn_scan.disabled = False
                btn_scan.label = "Escanear"
                count = len(self._installed_model_names)
                if provider == "ollama":
                    if count > 0:
                        self.notify(
                            f"Detectados {count} modelos en Ollama local.",
                            title="Escaneo Exitoso",
                            severity="information",
                        )
                    else:
                        self.notify(
                            "No se detectaron modelos en Ollama local.",
                            title="Sin Modelos",
                            severity="warning",
                        )
                else:
                    self.notify(
                        f"Catálogo de modelos actualizado para {provider.upper()}.",
                        title="Catálogo Actualizado",
                    )
        except Exception:
            pass

    def _format_choices_and_status(
        self,
        provider: str,
        current_model: str,
        discovered: List[Tuple[str, str]],
    ) -> Tuple[List[Tuple[str, str]], str, str]:
        """Format dropdown choices and status label from discovered list."""
        installed_ids = {m_id for _, m_id in discovered}
        choices: List[Tuple[str, str]] = list(discovered)

        if current_model and current_model not in installed_ids:
            if provider == "ollama":
                choices.insert(0, (f"[!] {current_model} (No instalado en Ollama)", current_model))
            else:
                choices.insert(0, (f"{current_model} (Actual)", current_model))

        choices.append(("Personalizado / Otro...", "__custom__"))

        valid_values = {val for _, val in choices}
        selected_val = current_model if current_model in valid_values else (discovered[0][1] if discovered else "")

        if provider == "ollama":
            if self._installed_model_names:
                count = len(self._installed_model_names)
                if current_model and current_model not in self._installed_model_names:
                    status = (
                        f"[bold yellow][!] El modelo '{current_model}' no está instalado en Ollama. "
                        f"Selecciona uno de los {count} modelos detectados arriba.[/]"
                    )
                else:
                    status = f"[bold green][✓] {count} modelos instalados detectados en Ollama local.[/]"
            else:
                status = "[dim yellow]Ollama no respondió en el host; mostrando catálogo sugerido.[/]"
        else:
            status = f"[dim]Catálogo oficial de modelos recomendados para {provider.upper()}.[/dim]"

        return choices, selected_val, status

    def _build_model_choices(
        self,
        provider: str,
        current_model: str,
        host: Optional[str] = None,
        force_refresh: bool = False,
        allow_network: bool = True,
    ) -> Tuple[List[Tuple[str, str]], str, str]:
        """Build choices for Select dropdown, determine initial selection and status message."""
        discovered = discover_provider_models(
            provider, host=host, force_refresh=force_refresh, allow_network=allow_network
        )
        self._installed_model_names = {m_id for _, m_id in discovered}
        return self._format_choices_and_status(provider, current_model, discovered)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Dynamically update input labels, password masking, and models when provider changes."""
        if event.select.id == "select-provider" and event.value != Select.BLANK:
            self._update_provider_fields(str(event.value))
        elif event.select.id == "select-model" and event.value != Select.BLANK:
            val = str(event.value)
            inp_model = self.query_one("#input-model", Input)
            if val != "__custom__":
                inp_model.value = val
                provider = str(self.query_one("#select-provider", Select).value)
                self._update_status_for_model(provider, val)
            else:
                inp_model.focus()

    def _update_status_for_model(self, provider: str, model_id: str) -> None:
        lbl_status = self.query_one("#lbl-model-status", Label)
        if provider == "ollama":
            if model_id in self._installed_model_names:
                lbl_status.update(f"[bold green][✓] Modelo instalado seleccionado: {model_id}[/]")
            else:
                lbl_status.update(f"[bold yellow][!] Modelo seleccionado no verificado en Ollama: {model_id}[/]")
        else:
            lbl_status.update(f"[dim]Modelo seleccionado: {model_id}[/dim]")

    def _update_provider_fields(self, provider: str) -> None:
        meta = self.PROVIDER_METADATA.get(provider, self.PROVIDER_METADATA["ollama"])
        lbl_cred = self.query_one("#lbl-credential", Label)
        inp_cred = self.query_one("#input-api-key", Input)
        lbl_help = self.query_one("#lbl-provider-help", Label)
        inp_model = self.query_one("#input-model", Input)
        sel_model = self.query_one("#select-model", Select)
        lbl_status = self.query_one("#lbl-model-status", Label)

        lbl_cred.update(meta["label"])
        lbl_help.update(meta["help"])
        inp_cred.placeholder = meta["placeholder"]
        inp_cred.password = meta["is_secret"]

        if meta["is_secret"]:
            stored = vault.decrypt(db.get_setting(meta["setting_key"])) or ""
        else:
            stored = db.get_setting(meta["setting_key"]) or meta["default_val"]
        inp_cred.value = stored

        # Refresh model options with ZERO LAG (allow_network=False)
        host = stored if provider == "ollama" else None
        choices, sel_val, status_msg = self._build_model_choices(
            provider, inp_model.value.strip(), host=host, allow_network=False
        )
        sel_model.set_options(choices)
        if sel_val:
            sel_model.value = sel_val
            inp_model.value = sel_val
        lbl_status.update(status_msg)

        # If switching to Ollama and not yet cached, scan in background
        if provider == "ollama" and get_cached_ollama_models(host=host) is None:
            self.run_background_scan(is_manual=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-vault":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-scan-models":
            self.action_scan_models()

    def action_scan_models(self) -> None:
        """Scan models on the configured host or reload catalog asynchronously."""
        self.run_background_scan(is_manual=True)

    def action_save(self) -> None:
        provider = str(self.query_one("#select-provider", Select).value)
        model = self.query_one("#input-model", Input).value.strip()
        cred_val = self.query_one("#input-api-key", Input).value.strip()
        auto_approve = self.query_one("#chk-auto", Checkbox).value

        # Fallback to select-model if input-model is empty
        if not model:
            sel_val = str(self.query_one("#select-model", Select).value)
            if sel_val and sel_val != "__custom__":
                model = sel_val

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
