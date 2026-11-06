"""CLI Entrypoint for the Networking Agent."""

import argparse
import os
import sys

from pydantic import SecretStr

from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.models.device import DeviceInventory
from networking_agent.models.telemetry import TelemetryEvent


def cli_entrypoint() -> None:
    """Parses command-line arguments and runs the agent."""
    parser = argparse.ArgumentParser(description="NetworkingAgent: Enterprise Closed-Loop Network Assistant")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "anthropic"],
        default="ollama",
        help="AI Provider to use (default: ollama)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specific model name (e.g., llama3.1, gpt-4o, claude-3-5-sonnet-latest)",
    )
    parser.add_argument(
        "--device-host",
        type=str,
        default="10.10.20.11",
        help="Device IP or hostname",
    )
    parser.add_argument(
        "--device-type",
        type=str,
        default="cisco_nxos",
        help="Device platform (cisco_ios, cisco_nxos, cisco_xr, juniper_junos)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip interactive confirmation (use with caution!)",
    )
    parser.add_argument(
        "--log-message",
        type=str,
        default=(
            "%OSPF-4-NONEIGHBOR: OSPF process 1, Neighbor 10.0.0.2 on interface Ethernet1/1 "
            "stuck in EXSTART/EXCHANGE state. Neighbor MTU 9216 is larger than local interface MTU 1500."
        ),
        help="Syslog or telemetry event text to analyze",
    )

    args = parser.parse_args()

    # Build device inventory safely
    net_pass = os.environ.get("NET_PASS")
    device = DeviceInventory(
        host=args.device_host,
        device_type=args.device_type,  # type: ignore
        username=os.environ.get("NET_USER", "admin"),
        password=SecretStr(net_pass) if net_pass else None,
    )

    event = TelemetryEvent(
        raw_text=args.log_message,
        source_host=args.device_host,
    )

    agent = NetworkAssistantAgent(
        ai_provider=args.provider,
        ai_model=args.model,
        auto_approve=args.auto_approve,
    )

    success = agent.process_telemetry(device=device, telemetry=event, mode="CLI_REACTIVE")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    cli_entrypoint()
