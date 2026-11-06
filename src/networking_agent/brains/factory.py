"""Factory for instantiating LLM brains."""

from typing import Optional

from networking_agent.brains.anthropic import AnthropicBrain
from networking_agent.brains.base import LLMBrain
from networking_agent.brains.gemini import GeminiBrain
from networking_agent.brains.ollama import OllamaBrain
from networking_agent.brains.openai import OpenAIBrain
from networking_agent.core.config import settings


def get_ai_brain(provider: Optional[str] = None, model: Optional[str] = None) -> LLMBrain:
    """Factory to switch AI providers cleanly without changing business logic."""
    chosen_provider = (provider or settings.ai_provider).lower()
    chosen_model = model or settings.ai_model

    if chosen_provider == "ollama":
        return OllamaBrain(model_name=chosen_model or "llama3.1")
    elif chosen_provider == "gemini":
        return GeminiBrain(model_name=chosen_model or "gemini-3.8-flash")
    elif chosen_provider == "openai":
        return OpenAIBrain(model_name=chosen_model or "gpt-4o")
    elif chosen_provider == "anthropic":
        return AnthropicBrain(model_name=chosen_model or "claude-3-5-sonnet-latest")

    raise ValueError(f"Unsupported AI Brain provider: '{chosen_provider}'")
