"""Local, private inference provider using Ollama with structured schema."""

from typing import Optional

from networking_agent.brains.base import HARDENED_CONFIG_SYSTEM_PROMPT, HARDENED_SYSTEM_PROMPT, LLMBrain
from networking_agent.core.config import settings
from networking_agent.core.exceptions import AIAnalysisError
from networking_agent.core.logging import logger
from networking_agent.models.config_intent import ConfigurationIntent
from networking_agent.models.intent import NetworkIntent


class OllamaBrain(LLMBrain):
    """Local inference using Ollama (e.g., llama3.1, qwen2.5-coder)."""

    def __init__(self, model_name: str = "llama3.1", host: Optional[str] = None):
        self.model_name = model_name
        self.host = host or settings.ollama_host

    def analyze_event(self, telemetry_data: str) -> NetworkIntent:
        try:
            from ollama import Client

            client = Client(host=self.host)
            user_content = (
                f"Analyze this network event and emit the remediation intent:\n"
                f"<telemetry_event>\n{telemetry_data}\n</telemetry_event>"
            )

            response = client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": HARDENED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                format=NetworkIntent.model_json_schema(),
                options={"temperature": 0},
            )
            return NetworkIntent.model_validate_json(response.message.content)
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                try:
                    from ollama import Client

                    client = Client(host=self.host)
                    models_response = client.list()
                    available = [m.model for m in models_response.models if hasattr(m, "model")]
                    if available:
                        error_msg = (
                            f"Model '{self.model_name}' is not installed in Ollama.\n"
                            f"Installed models found on your machine: {available}\n"
                            f"-> To download it, run: 'ollama pull {self.model_name}'\n"
                            f"-> Or run with an installed model, e.g.: uv run networking-agent --model {available[0]}"
                        )
                except Exception:
                    pass
            logger.error(f"[bold red]Ollama Brain analysis failed:[/bold red] {error_msg}")
            raise AIAnalysisError(f"Ollama inference error: {error_msg}") from e

    def synthesize_configuration(
        self,
        device_host: str,
        vendor_family: str,
        natural_request: str,
        protocol_hint: Optional[str] = None,
    ) -> ConfigurationIntent:
        try:
            from ollama import Client

            client = Client(host=self.host)
            hint_str = f" [Protocol Focus: {protocol_hint}]" if protocol_hint else ""
            user_content = (
                f"TARGET DEVICE: Host {device_host} | Operating System: {vendor_family}{hint_str}\n"
                f"OPERATOR CONFIGURATION REQUEST IN NATURAL LANGUAGE:\n"
                f"<configuration_request>\n{natural_request}\n</configuration_request>\n\n"
                f"Synthesize the complete, secure configuration change and emit ConfigurationIntent JSON."
            )

            response = client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": HARDENED_CONFIG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                format=ConfigurationIntent.model_json_schema(),
                options={"temperature": 0},
            )
            return ConfigurationIntent.model_validate_json(response.message.content)
        except Exception as e:
            logger.error(f"[bold red]Ollama Brain configuration synthesis failed:[/bold red] {e}")
            raise AIAnalysisError(f"Ollama configuration synthesis error: {e}") from e

