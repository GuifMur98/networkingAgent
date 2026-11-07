"""Factory for instantiating LLM brains with persisted vault settings."""

from typing import Optional

from networking_agent.brains.anthropic import AnthropicBrain
from networking_agent.brains.base import LLMBrain
from networking_agent.brains.gemini import GeminiBrain
from networking_agent.brains.ollama import OllamaBrain
from networking_agent.brains.openai import OpenAIBrain
from networking_agent.core.config import settings
from networking_agent.core.crypto import vault
from networking_agent.core.db import db


def get_ai_brain(provider: Optional[str] = None, model: Optional[str] = None) -> LLMBrain:
    """Factory to switch AI providers cleanly with credentials loaded from vault/db."""
    db_provider = db.get_setting("ai_provider")
    db_model = db.get_setting("ai_model")

    chosen_provider = (provider or db_provider or settings.ai_provider).lower()
    chosen_model = model or db_model or settings.ai_model

    if chosen_provider == "ollama":
        db_host = db.get_setting("ollama_host")
        return OllamaBrain(
            model_name=chosen_model or "llama3.1",
            host=db_host or settings.ollama_host,
        )
    elif chosen_provider == "gemini":
        db_key = vault.decrypt(db.get_setting("gemini_api_key"))
        return GeminiBrain(
            model_name=chosen_model or "gemini-3.8-flash",
            api_key=db_key,
        )
    elif chosen_provider == "openai":
        db_key = vault.decrypt(db.get_setting("openai_api_key"))
        return OpenAIBrain(
            model_name=chosen_model or "gpt-4o",
            api_key=db_key,
        )
    elif chosen_provider == "anthropic":
        db_key = vault.decrypt(db.get_setting("anthropic_api_key"))
        return AnthropicBrain(
            model_name=chosen_model or "claude-3-5-sonnet-latest",
            api_key=db_key,
        )

    raise ValueError(f"Unsupported AI Brain provider: '{chosen_provider}'")
