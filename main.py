"""NetworkingAgent - Enterprise Autonomous Network Assistant.

Main entrypoint for development and direct execution.
"""

import os

from pydantic import SecretStr

from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.models.device import DeviceInventory
from networking_agent.models.telemetry import TelemetryEvent


def main() -> None:
    # 1. Device inventory configured securely (without plaintext password fallbacks)
    net_pass = os.environ.get("NET_PASS")
    leaf_nxos = DeviceInventory(
        device_type="cisco_nxos",
        host="10.10.20.11",
        username=os.environ.get("NET_USER", "admin"),
        password=SecretStr(net_pass) if net_pass else None,
    )

    # 2. Select AI Provider ("ollama", "openai", "anthropic")
    # For local inference without API keys, Ollama with llama3.1 is the default
    agent = NetworkAssistantAgent(ai_provider="ollama", ai_model="llama3.1")

    # 3. Simulated critical telemetry captured by Syslog
    syslog_event = TelemetryEvent(
        raw_text=(
            "%OSPF-4-NONEIGHBOR: OSPF process 1, Neighbor 10.0.0.2 on interface Ethernet1/1 "
            "stuck in EXSTART/EXCHANGE state. Neighbor MTU 9216 is larger than local interface MTU 1500."
        ),
        source_host=leaf_nxos.host,
    )

    # 4. Closed-loop execution: AI Diagnosis -> Guardrails -> HitL -> Pre-Check -> Execute -> Post-Check -> Rollback
    agent.process_telemetry(device=leaf_nxos, telemetry=syslog_event, mode="REACTIVE")


if __name__ == "__main__":
    main()
