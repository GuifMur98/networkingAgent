"""Application configuration management using Pydantic Settings."""

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Global configuration for the Networking Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI Brain Provider Defaults
    ai_provider: str = Field(default="ollama", description="Default AI provider: ollama, openai, anthropic")
    ai_model: Optional[str] = Field(default=None, description="Specific model name override")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API base URL")

    # Security & Blast Radius
    enforce_guardrails: bool = Field(default=True, description="Strict enforcement of blast radius and sanitization")
    protected_interfaces: List[str] = Field(
        default_factory=lambda: [
            "Management0",
            "mgmt0",
            "GigabitEthernet0/0",
            "fxp0",
            "em0",
            "Loopback0",
        ],
        description="Interfaces forbidden from being disabled or modified autonomously",
    )
    max_mtu: int = Field(default=9216, description="Maximum allowed MTU value")
    min_mtu: int = Field(default=68, description="Minimum allowed MTU value")

    # Operations & Backups
    backup_dir: Path = Field(default=Path("backups"), description="Directory where device running-configs are saved")
    audit_log_path: Path = Field(default=Path("logs/audit.jsonl"), description="Path to immutable audit trail")
    ssh_timeout: int = Field(default=30, description="SSH connection timeout in seconds")
    auto_rollback_on_failure: bool = Field(default=True, description="Trigger automatic rollback if verification fails")


# Singleton instance
settings = AgentSettings()
