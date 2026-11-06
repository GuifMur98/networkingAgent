"""Cisco NX-OS Driver with transactional sessions and checkpoints."""

from pathlib import Path
from typing import List, Optional

from netmiko import ConnectHandler

from networking_agent.core.logging import logger
from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.models.intent import NetworkIntent

CHECKPOINT_NAME = "PRE_AI_REMEDIATION"


class CiscoNXOSDriver(NetworkOSDriver):
    """Driver for Cisco Nexus switches (NX-OS) using atomic sessions and checkpoints."""

    def get_health_commands(self) -> List[str]:
        return [
            "show bgp l2vpn evpn summary",
            "show ip ospf neighbors",
            "show interface status err-disabled",
        ]

    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        cmds = ["configure session AI_AGENT_FIX"]
        if intent.action == "disable_interface" and intent.target_interface:
            cmds.extend([f"interface {intent.target_interface}", "shutdown"])
        elif intent.action == "enable_interface" and intent.target_interface:
            cmds.extend([f"interface {intent.target_interface}", "no shutdown"])
        elif intent.action == "set_interface_mtu" and intent.target_interface and intent.mtu_value:
            cmds.extend([f"interface {intent.target_interface}", f"mtu {intent.mtu_value}"])
        elif intent.action == "reset_bgp_neighbor" and intent.bgp_neighbor_ip:
            cmds.extend(
                [
                    f"clear bgp all {intent.bgp_neighbor_ip} soft",
                ]
            )
        cmds.append("commit")
        return cmds

    def backup_running_config(self) -> Path:
        """Takes a remote hardware checkpoint on NX-OS and also downloads a local copy."""
        backup_path = super().backup_running_config()
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                logger.info(f"[*] Creating NX-OS remote checkpoint '{CHECKPOINT_NAME}'...")
                conn.send_command(f"checkpoint {CHECKPOINT_NAME}")
        except Exception as e:
            logger.warning(f"[yellow]Could not create remote checkpoint {CHECKPOINT_NAME}: {e}[/yellow]")
        return backup_path

    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Restores the configuration using NX-OS checkpoint rollback."""
        logger.info(f"[*] Rolling back NX-OS configuration to checkpoint '{CHECKPOINT_NAME}'...")
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                out = conn.send_command(f"rollback running-config checkpoint {CHECKPOINT_NAME}")
                logger.info(f"[green]NX-OS rollback output:[/green]\n{out}")
                return True
        except Exception as e:
            logger.error(f"[bold red]NX-OS rollback failed:[/bold red] {e}")
            return False
