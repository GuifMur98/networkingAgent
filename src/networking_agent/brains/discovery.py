"""Model discovery and catalog services for AI providers."""

import time
from typing import Any, Dict, List, Optional, Tuple

from networking_agent.core.config import settings
from networking_agent.core.db import db
from networking_agent.core.logging import logger

# In-memory cache for discovered Ollama models: {host: (timestamp, models)}
_OLLAMA_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 60.0


def get_installed_ollama_models(host: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Query live Ollama instance for locally installed models with memory caching."""
    target_host = host or db.get_setting("ollama_host") or settings.ollama_host

    # Return cached results if valid and not forcing refresh
    if not force_refresh and target_host in _OLLAMA_CACHE:
        cached_time, cached_models = _OLLAMA_CACHE[target_host]
        if time.time() - cached_time < _CACHE_TTL_SECONDS:
            return cached_models

    try:
        from ollama import Client

        client = Client(host=target_host, timeout=2.5)
        resp = client.list()
        results = []
        for m in getattr(resp, "models", []):
            m_name = getattr(m, "model", None) or getattr(m, "name", None)
            if not m_name:
                continue
            details = getattr(m, "details", None)
            param_size = getattr(details, "parameter_size", None) if details else None
            results.append({
                "model": str(m_name),
                "param_size": str(param_size) if param_size else "",
            })

        _OLLAMA_CACHE[target_host] = (time.time(), results)
        return results
    except Exception as e:
        logger.debug(f"Failed to query Ollama models on {target_host}: {e}")
        return []


def discover_provider_models(
    provider: str,
    host: Optional[str] = None,
    api_key: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Tuple[str, str]]:
    """Return discovered live models or recommended official catalog for the given provider."""
    provider = provider.lower()

    if provider == "ollama":
        installed = get_installed_ollama_models(host=host, force_refresh=force_refresh)
        if installed:
            choices = []
            for item in installed:
                size_suffix = f" [{item['param_size']}]" if item["param_size"] else ""
                choices.append((f"{item['model']}{size_suffix} (Instalado)", item["model"]))
            return choices

        # Fallback catalog when Ollama is offline or has no local models
        return [
            ("qwen2.5-coder:14b (Recomendado)", "qwen2.5-coder:14b"),
            ("qwen3-coder:30b", "qwen3-coder:30b"),
            ("netexpert:latest", "netexpert:latest"),
            ("llama3.1:8b (Estandar)", "llama3.1"),
        ]

    elif provider == "gemini":
        return [
            ("Gemini 2.5 Flash (Recomendado / Rapido)", "gemini-2.5-flash"),
            ("Gemini 2.5 Pro (Razonamiento Complejo)", "gemini-2.5-pro"),
            ("Gemini 2.0 Flash", "gemini-2.0-flash"),
            ("Gemini 1.5 Pro", "gemini-1.5-pro"),
        ]

    elif provider == "openai":
        return [
            ("GPT-4o (Recomendado / Inteligente)", "gpt-4o"),
            ("GPT-4o Mini (Rapido y Economico)", "gpt-4o-mini"),
            ("o1-mini (Razonamiento STEM)", "o1-mini"),
            ("o3-mini (Alta Precision)", "o3-mini"),
        ]

    elif provider == "anthropic":
        return [
            ("Claude 3.5 Sonnet (Recomendado)", "claude-3-5-sonnet-latest"),
            ("Claude 3.5 Haiku (Rapido)", "claude-3-5-haiku-latest"),
            ("Claude 3 Opus (Razonamiento Profundo)", "claude-3-opus-latest"),
        ]

    return []
