"""MikroTik RouterOS Driver for automated diagnosis, snapshot and remediation."""

from pathlib import Path
from typing import List, Optional

from networking_agent.core.logging import logger
from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.models.intent import NetworkIntent

MIKROTIK_BACKUP_NAME = "before_ai_remediation"


class MikrotikRouterOSDriver(NetworkOSDriver):
    """Driver for MikroTik RouterOS devices (v6 and v7)."""

    def get_health_commands(self) -> List[str]:
        return [
            "/system resource print",
            "/interface print stats",
            "/interface ethernet print detail",
            "/ip dns print",
            "/interface print terse",
            "/ip route print count-only",
        ]

    def get_gateway_interfaces(self) -> List[str]:
        """Identifies WAN or primary uplink interfaces on MikroTik to prevent accidental remote cutoff."""
        return [
            "ether1",
            "sfp1",
            "sfp-sfpplus1",
            "lte1",
            "pppoe-out1",
            "wan",
            "uplink",
            "internet",
            "gateway",
            "bridge",
            "lo",
        ]

    def get_rollback_description(self) -> str:
        return f"MikroTik system backup snapshot ('{MIKROTIK_BACKUP_NAME}.backup') and export file"

    def get_running_config_command(self) -> str:
        """In RouterOS, /export verbose=no exports the active human-readable configuration."""
        return "/export verbose=no"

    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        if intent.action == "disable_interface" and intent.target_interface:
            return [f'/interface set [find name="{intent.target_interface}"] disabled=yes']
        elif intent.action == "enable_interface" and intent.target_interface:
            return [f'/interface set [find name="{intent.target_interface}"] disabled=no']
        elif intent.action == "restart_interface" and intent.target_interface:
            return [
                f'/interface set [find name="{intent.target_interface}"] disabled=yes',
                f'/interface set [find name="{intent.target_interface}"] disabled=no',
            ]
        elif intent.action == "set_interface_duplex_full" and intent.target_interface:
            return [
                f'/interface ethernet set [find name="{intent.target_interface}"] auto-negotiation=yes full-duplex=yes'
            ]
        elif intent.action == "set_interface_mtu" and intent.target_interface and intent.mtu_value:
            return [f'/interface set [find name="{intent.target_interface}"] mtu={intent.mtu_value}']
        elif intent.action == "reset_bgp_neighbor" and intent.bgp_neighbor_ip:
            # Works across RouterOS v7 and v6 connection/peer definitions
            return [
                f'/routing bgp connection disable [find remote.address="{intent.bgp_neighbor_ip}"]',
                f'/routing bgp connection enable [find remote.address="{intent.bgp_neighbor_ip}"]',
            ]
        elif intent.action == "clear_arp_cache":
            return ["/ip arp remove [find]"]
        return []

    def backup_running_config(self) -> Path:
        """Downloads full configuration export and generates hardware backup on RouterOS."""
        backup_path = super().backup_running_config()
        try:
            conn = self.get_connection()
            logger.info(f"[*] Creating MikroTik hardware backup '{MIKROTIK_BACKUP_NAME}'...")
            conn.send_command(f"/system backup save name={MIKROTIK_BACKUP_NAME}")
        except Exception as e:
            logger.warning(f"[yellow]Could not create RouterOS internal backup file: {e}[/yellow]")
        return backup_path

    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Attempts to restore previous state on MikroTik RouterOS."""
        logger.info(f"[*] Executing rollback on MikroTik RouterOS {self.device.host}...")
        try:
            conn = self.get_connection()
            # In MikroTik, loading a backup reboots or restores the configuration
            out = conn.send_command(f"/system backup load name={MIKROTIK_BACKUP_NAME}.backup")
            logger.info(f"[green]MikroTik rollback executed:[/green]\n{out}")
            return True
        except Exception as e:
            logger.error(f"[bold red]MikroTik rollback failed:[/bold red] {e}")
            return False

    def _bgp_diag_commands(self) -> List[str]:
        return ["/routing bgp session print", "/routing bgp connection print"]

    def _ospf_diag_commands(self) -> List[str]:
        return ["/routing ospf neighbor print", "/routing ospf interface print"]

    def _vlan_diag_commands(self) -> List[str]:
        return ["/interface vlan print", "/interface bridge vlan print"]

    def _stp_diag_commands(self) -> List[str]:
        return ["/interface bridge print", "/interface bridge port print"]

    def _channel_diag_commands(self) -> List[str]:
        return ["/interface bonding print"]

    def _acl_diag_commands(self) -> List[str]:
        return ["/ip firewall filter print"]
