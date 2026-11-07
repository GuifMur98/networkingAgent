"""OpenAI inference provider using strict Structured Outputs."""

import os
from typing import Optional

from networking_agent.brains.base import HARDENED_CONFIG_SYSTEM_PROMPT, HARDENED_SYSTEM_PROMPT, LLMBrain
from networking_agent.core.config import settings
from networking_agent.core.exceptions import AIAnalysisError
from networking_agent.core.logging import logger
from networking_agent.models.config_intent import ConfigurationIntent
from networking_agent.models.intent import NetworkIntent


class OpenAIBrain(LLMBrain):
    """Cloud inference using OpenAI with structured output parsing."""

    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        from openai import OpenAI

        key = api_key or settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise AIAnalysisError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=key)
        self.model_name = model_name

    def analyze_event(self, telemetry_data: str) -> NetworkIntent:
        try:
            user_content = (
                f"Analyze this network event and emit the remediation intent:\n"
                f"<telemetry_event>\n{telemetry_data}\n</telemetry_event>"
            )
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": HARDENED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=NetworkIntent,
                temperature=0,
            )
            parsed = completion.choices[0].message.parsed
            if not parsed:
                raise AIAnalysisError("OpenAI returned an empty parsed response.")
            return parsed
        except Exception as e:
            logger.error(f"[bold red]OpenAI Brain analysis failed:[/bold red] {e}")
            raise AIAnalysisError(f"OpenAI inference error: {e}") from e

    def synthesize_configuration(
        self,
        device_host: str,
        vendor_family: str,
        natural_request: str,
        protocol_hint: Optional[str] = None,
    ) -> ConfigurationIntent:
        try:
            hint_str = f" [Protocol Focus: {protocol_hint}]" if protocol_hint else ""
            user_content = (
                f"TARGET DEVICE: Host {device_host} | Operating System: {vendor_family}{hint_str}\n"
                f"OPERATOR CONFIGURATION REQUEST IN NATURAL LANGUAGE:\n"
                f"<configuration_request>\n{natural_request}\n</configuration_request>\n\n"
                f"Synthesize the complete, secure configuration change and emit ConfigurationIntent JSON."
            )
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": HARDENED_CONFIG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=ConfigurationIntent,
                temperature=0,
            )
            parsed = completion.choices[0].message.parsed
            if not parsed:
                raise AIAnalysisError("OpenAI returned an empty parsed response.")
            return parsed
        except Exception as e:
            logger.error(f"[bold red]OpenAI Brain configuration synthesis failed:[/bold red] {e}")
            raise AIAnalysisError(f"OpenAI configuration synthesis error: {e}") from e

