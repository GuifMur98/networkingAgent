"""Cisco IOS-XR Driver."""

from pathlib import Path
from typing import List, Optional

from netmiko import ConnectHandler

from networking_agent.core.logging import logger
from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.models.intent import NetworkIntent


class CiscoIOSXRDriver(NetworkOSDriver):
    """Driver for Cisco IOS-XR Carrier-Grade routers."""

    def get_health_commands(self) -> List[str]:
        return [
            "show ipv4 interface brief",
            "show processes cpu | include CPU",
            "show interfaces summary",
            "show route summary",
            "show ospf neighbor",
            "show bgp summary",
        ]

    def get_gateway_interfaces(self) -> List[str]:
        return [
            "mgmteth0/rp0/cpu0/0",
            "mgmteth0/0/cpu0/0",
            "mgmt0",
            "loopback0",
            "bundle-ether1",
            "wan",
            "uplink",
            "internet",
            "gateway",
        ]

    def get_rollback_description(self) -> str:
        return "Cisco IOS-XR atomic 'rollback configuration last 1'"

    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        cmds = []
        if intent.action == "disable_interface" and intent.target_interface:
            cmds = [f"interface {intent.target_interface}", "shutdown", "commit confirmed 180"]
        elif intent.action == "enable_interface" and intent.target_interface:
            cmds = [f"interface {intent.target_interface}", "no shutdown", "commit confirmed 180"]
        elif intent.action == "set_interface_mtu" and intent.target_interface and intent.mtu_value:
            cmds = [
                f"interface {intent.target_interface}",
                f"ipv4 mtu {intent.mtu_value}",
                "commit confirmed 180",
            ]
        elif intent.action == "reset_bgp_neighbor" and intent.bgp_neighbor_ip:
            cmds = [f"clear bgp {intent.bgp_neighbor_ip} soft"]
        return cmds

    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Rolls back the last commit on Cisco IOS-XR."""
        logger.info(f"[*] Rolling back last commit on IOS-XR {self.device.host}...")
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                out = conn.send_command("rollback configuration last 1")
                logger.info(f"[green]IOS-XR rollback executed:[/green]\n{out}")
                return True
        except Exception as e:
            logger.error(f"[bold red]IOS-XR rollback failed:[/bold red] {e}")
            return False
