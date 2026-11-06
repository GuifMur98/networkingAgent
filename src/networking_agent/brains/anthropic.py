"""Anthropic inference provider using Claude and tool use / json schema validation."""

import os
from typing import Optional

from networking_agent.brains.base import HARDENED_SYSTEM_PROMPT, LLMBrain
from networking_agent.core.config import settings
from networking_agent.core.exceptions import AIAnalysisError
from networking_agent.core.logging import logger
from networking_agent.models.intent import NetworkIntent


class AnthropicBrain(LLMBrain):
    """Cloud inference using Anthropic Claude with tool-enforced schema."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-latest", api_key: Optional[str] = None):
        import anthropic

        key = api_key or settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise AIAnalysisError("ANTHROPIC_API_KEY is not configured.")
        self.client = anthropic.Anthropic(api_key=key)
        self.model_name = model_name

    def analyze_event(self, telemetry_data: str) -> NetworkIntent:
        try:
            user_content = (
                f"Analyze this network event and emit the remediation intent:\n"
                f"<telemetry_event>\n{telemetry_data}\n</telemetry_event>"
            )
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                temperature=0,
                system=HARDENED_SYSTEM_PROMPT,
                tools=[
                    {
                        "name": "emit_network_intent",
                        "description": "Emits the structured diagnosis and network remediation intent.",
                        "input_schema": NetworkIntent.model_json_schema(),
                    }
                ],
                tool_choice={"type": "tool", "name": "emit_network_intent"},
                messages=[{"role": "user", "content": user_content}],
            )
            tool_input = response.content[0].input
            return NetworkIntent.model_validate(tool_input)
        except Exception as e:
            logger.error(f"[bold red]Anthropic Brain analysis failed:[/bold red] {e}")
            raise AIAnalysisError(f"Anthropic inference error: {e}") from e
