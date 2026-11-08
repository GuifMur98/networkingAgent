"""Application configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import List, Optional

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_app_data_dir() -> Path:
    """Returns the anchored secure data directory for the application.

    Priority:
    1. NETWORKING_AGENT_DATA_DIR environment variable
    2. Local ./data directory IF running inside a local development repository (pyproject.toml present)
    3. platformdirs.user_data_dir("NetworkingAgent", appauthor=False) / "data"
    """
    env_dir = os.environ.get("NETWORKING_AGENT_DATA_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "src" / "networking_agent").exists():
        p = (cwd / "data").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    p = Path(platformdirs.user_data_dir("NetworkingAgent", appauthor=False)) / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def get_app_log_dir() -> Path:
    """Returns the anchored log directory for the application."""
    env_log = os.environ.get("NETWORKING_AGENT_LOG_DIR")
    if env_log:
        p = Path(env_log).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "src" / "networking_agent").exists():
        p = (cwd / "logs").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    p = Path(platformdirs.user_data_dir("NetworkingAgent", appauthor=False)) / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


class AgentSettings(BaseSettings):
    """Global configuration for the Networking Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI Brain Provider Defaults
    ai_provider: str = Field(default="ollama", description="Default AI provider: ollama, gemini, openai, anthropic")
    ai_model: Optional[str] = Field(default=None, description="Specific model name override")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API base URL")

    # Security & Blast Radius
    enforce_guardrails: bool = Field(default=True, description="Strict enforcement of blast radius and sanitization")
    protected_interfaces: List[str] = Field(
        default_factory=lambda: [
            # Cisco IOS / IOS-XE
            "Management0",
            "mgmt0",
            "GigabitEthernet0/0",
            "GigabitEthernet0/0/0",
            "FastEthernet0/0",
            "Loopback0",
            "Dialer0",
            "Dialer1",
            "Tunnel0",
            # Cisco IOS-XR
            "MgmtEth0/RP0/CPU0/0",
            "MgmtEth0/0/CPU0/0",
            # Juniper Junos
            "fxp0",
            "em0",
            "me0",
            "vme",
            "lo0",
            # MikroTik RouterOS
            "ether1",
            "sfp1",
            "sfp-sfpplus1",
            "lte1",
            "pppoe-out1",
            "bridge",
            # Generic Uplink / WAN terms
            "wan",
            "uplink",
            "gateway",
            "internet",
        ],
        description="Interfaces forbidden from being disabled or modified autonomously across all vendors",
    )
    max_mtu: int = Field(default=9216, description="Maximum allowed MTU value")
    min_mtu: int = Field(default=68, description="Minimum allowed MTU value")

    # Operations & Backups
    backup_dir: Path = Field(
        default_factory=lambda: get_app_data_dir() / "backups",
        description="Directory where device running-configs are saved",
    )
    audit_log_path: Path = Field(
        default_factory=lambda: get_app_log_dir() / "audit.jsonl",
        description="Path to immutable audit trail",
    )
    ssh_timeout: int = Field(default=30, description="SSH connection timeout in seconds")
    auto_rollback_on_failure: bool = Field(default=True, description="Trigger automatic rollback if verification fails")
    auto_approve: bool = Field(default=False, description="Skip Human-in-the-Loop authorization gate")


# Singleton instance
settings = AgentSettings()
