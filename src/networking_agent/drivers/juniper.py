"""Juniper Junos Driver."""

from pathlib import Path
from typing import List, Optional

from networking_agent.core.logging import logger
from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.models.intent import NetworkIntent


class JuniperJunosDriver(NetworkOSDriver):
    """Driver for Juniper Junos multi-vendor support."""

    def get_health_commands(self) -> List[str]:
        return [
            "show interfaces terse",
            "show chassis routing-engine",
            "show interfaces extensive | match \"Errors|Drops|Duplex\"",
            "show route summary",
            "show system uptime",
            "show ospf neighbor",
            "show bgp summary",
        ]

    def get_gateway_interfaces(self) -> List[str]:
        return [
            "fxp0",
            "em0",
            "me0",
            "vme",
            "lo0",
            "ge-0/0/0",
            "xe-0/0/0",
            "wan",
            "uplink",
            "internet",
            "gateway",
        ]

    def get_rollback_description(self) -> str:
        return "Junos commit confirmed with automatic 3-minute rollback timer"

    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        if intent.action == "disable_interface" and intent.target_interface:
            return [
                f"set interfaces {intent.target_interface} disable",
                "commit confirmed 3",
            ]
        elif intent.action == "enable_interface" and intent.target_interface:
            return [
                f"delete interfaces {intent.target_interface} disable",
                "commit confirmed 3",
            ]
        elif intent.action == "restart_interface" and intent.target_interface:
            return [
                f"set interfaces {intent.target_interface} disable",
                f"delete interfaces {intent.target_interface} disable",
                "commit confirmed 3",
            ]
        elif intent.action == "set_interface_duplex_full" and intent.target_interface:
            return [
                f"set interfaces {intent.target_interface} gigether-options full-duplex",
                "commit confirmed 3",
            ]
        elif intent.action == "set_interface_mtu" and intent.target_interface and intent.mtu_value:
            return [
                f"set interfaces {intent.target_interface} mtu {intent.mtu_value}",
                "commit confirmed 3",
            ]
        elif intent.action == "reset_bgp_neighbor" and intent.bgp_neighbor_ip:
            return [f"clear bgp neighbor {intent.bgp_neighbor_ip}"]
        elif intent.action == "clear_arp_cache":
            return ["clear arp"]
        return []

    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Rolls back the configuration to the previous commit on Junos."""
        logger.info(f"[*] Rolling back Junos configuration on {self.device.host}...")
        try:
            conn = self.get_connection()
            out = conn.send_config_set(["rollback 1", "commit and-quit"])
            logger.info(f"[green]Junos rollback output:[/green]\n{out}")
            return True
        except Exception as e:
            logger.error(f"[bold red]Junos rollback failed:[/bold red] {e}")
            return False
