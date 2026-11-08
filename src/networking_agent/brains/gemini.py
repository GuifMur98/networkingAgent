"""Google Gemini inference provider using the official modern google-genai SDK."""

import os
from typing import Optional

from networking_agent.brains.base import HARDENED_CONFIG_SYSTEM_PROMPT, HARDENED_SYSTEM_PROMPT, LLMBrain
from networking_agent.core.config import settings
from networking_agent.core.exceptions import AIAnalysisError
from networking_agent.core.logging import logger
from networking_agent.models.config_intent import ConfigurationIntent
from networking_agent.models.intent import NetworkIntent


class GeminiBrain(LLMBrain):
    """Cloud inference using Google Gemini with strict Pydantic Structured Outputs."""

    def __init__(self, model_name: str = "gemini-3.8-flash", api_key: Optional[str] = None):
        try:
            from google import genai
        except ImportError as e:
            raise AIAnalysisError(
                "The 'google-genai' library is required to use the Gemini provider. "
                "Install it using: uv pip install google-genai"
            ) from e

        key = api_key or settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise AIAnalysisError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )

        self.client = genai.Client(api_key=key)
        self.model_name = model_name

    def analyze_event(self, telemetry_data: str) -> NetworkIntent:
        try:
            from google.genai import types

            user_content = (
                f"Analyze this network event and emit the remediation intent:\n"
                f"<telemetry_event>\n{telemetry_data}\n</telemetry_event>"
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=HARDENED_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=NetworkIntent,
                    temperature=0.0,
                ),
            )

            if not response.text:
                raise AIAnalysisError("Gemini API returned an empty text response.")

            return NetworkIntent.model_validate_json(response.text)
        except Exception as e:
            logger.error(f"[bold red]Gemini Brain analysis failed:[/bold red] {e}")
            raise AIAnalysisError(f"Gemini inference error: {e}") from e

    def synthesize_configuration(
        self,
        device_host: str,
        vendor_family: str,
        natural_request: str,
        protocol_hint: Optional[str] = None,
        existing_config: Optional[str] = None,
    ) -> ConfigurationIntent:
        try:
            from google.genai import types

            hint_str = f" [Protocol Focus: {protocol_hint}]" if protocol_hint else ""
            user_content = (
                f"TARGET DEVICE: Host {device_host} | Operating System: {vendor_family}{hint_str}\n"
                f"OPERATOR CONFIGURATION REQUEST IN NATURAL LANGUAGE:\n"
                f"<configuration_request>\n{natural_request}\n</configuration_request>\n\n"
            )
            if existing_config:
                user_content += (
                    f"EXISTING RUNNING CONFIGURATION (INSPECT TO PRESERVE ACTIVE SERVICES & PREVENT COLLISIONS):\n"
                    f"<running_configuration>\n{existing_config}\n</running_configuration>\n\n"
                )
            user_content += (
                "Analyze existing state, perform conflict checks, synthesize the complete non-destructive "
                "configuration change, and emit ConfigurationIntent JSON."
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=HARDENED_CONFIG_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ConfigurationIntent,
                    temperature=0.0,
                ),
            )
            return ConfigurationIntent.model_validate_json(response.text)
        except Exception as e:
            logger.error(f"[bold red]Gemini Brain configuration synthesis failed:[/bold red] {e}")
            raise AIAnalysisError(f"Gemini configuration synthesis error: {e}") from e

