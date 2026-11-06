"""Cisco IOS and IOS-XE Driver."""

from pathlib import Path
from typing import List, Optional

from netmiko import ConnectHandler

from networking_agent.core.logging import logger
from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.models.intent import NetworkIntent


class CiscoIOSDriver(NetworkOSDriver):
    """Driver for Cisco IOS and IOS-XE platforms (Catalyst, ISR, ASR)."""

    def get_health_commands(self) -> List[str]:
        return [
            "show ip interface brief",
            "show interfaces status",
            "show interfaces counters errors",
            "show ip ospf neighbor",
            "show interfaces status err-disabled",
        ]

    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        if intent.action == "disable_interface" and intent.target_interface:
            return [f"interface {intent.target_interface}", "shutdown"]
        elif intent.action == "enable_interface" and intent.target_interface:
            return [f"interface {intent.target_interface}", "no shutdown"]
        elif intent.action == "restart_interface" and intent.target_interface:
            return [f"interface {intent.target_interface}", "shutdown", "no shutdown"]
        elif intent.action == "set_interface_duplex_full" and intent.target_interface:
            return [f"interface {intent.target_interface}", "speed auto", "duplex full"]
        elif intent.action == "set_interface_mtu" and intent.target_interface and intent.mtu_value:
            return [f"interface {intent.target_interface}", f"ip mtu {intent.mtu_value}"]
        elif intent.action == "reset_bgp_neighbor" and intent.bgp_neighbor_ip:
            return [f"clear ip bgp {intent.bgp_neighbor_ip}"]
        elif intent.action == "clear_arp_cache":
            return ["clear arp-cache"]
        return []

    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Restores config via configure replace if a backup path is provided."""
        if not backup_reference or not backup_reference.exists():
            logger.warning("[yellow]No local backup file provided for Cisco IOS rollback.[/yellow]")
            return False

        logger.info(f"[*] Attempting rollback on {self.device.host} using {backup_reference.name}...")
        try:
            # Transfer and execute configure replace or re-apply reverse operations
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                output = conn.send_command(f"configure replace flash:{backup_reference.name} force")
                logger.info(f"[green]Rollback executed:[/green]\n{output}")
                return True
        except Exception as e:
            logger.error(f"[bold red]Rollback failed on {self.device.host}:[/bold red] {e}")
            return False
