"""Base driver abstraction with real backup, verification, and rollback interfaces."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from netmiko import ConnectHandler

from networking_agent.core.config import settings
from networking_agent.core.exceptions import DeviceConnectionError
from networking_agent.core.logging import logger
from networking_agent.guardrails.validator import CommandValidator
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


class NetworkOSDriver(ABC):
    """Abstract base class for vendor-specific OS drivers."""

    def __init__(self, device: DeviceInventory):
        self.device = device
        self.backup_dir = settings.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def build_candidate_commands(self, intent: NetworkIntent) -> List[str]:
        """Translates a sanitized NetworkIntent into native OS CLI commands."""
        pass

    @abstractmethod
    def get_health_commands(self) -> List[str]:
        """Returns read-only diagnostic commands used for pre and post health verification."""
        pass

    def get_gateway_interfaces(self) -> List[str]:
        """Identifies interfaces carrying default routes or WAN uplinks to protect them from accidental cutoff."""
        return ["wan", "uplink", "internet", "gateway", "dialer"]

    def get_rollback_description(self) -> str:
        """Describes the vendor-specific rollback safety mechanism available for this platform."""
        return "Local configuration snapshot restore"

    def discover_active_management_interfaces(self, health_data: Optional[Dict[str, str]] = None) -> List[str]:
        """Dynamically identifies the interface carrying the SSH management IP or default route.

        Inspects live outputs from health check commands across any vendor (Cisco, Juniper, MikroTik)
        to discover which interface owns self.device.host, preventing loss of management.
        """
        discovered = list(self.get_gateway_interfaces())
        host_target = self.device.host.strip().lower()

        if health_data:
            import re

            for _, output in health_data.items():
                for line in output.splitlines():
                    # Check if line mentions the target IP
                    if host_target in line.lower():
                        # RouterOS: e.g. '0 R name="ether1" ...' or 'address=192.168.99.1/24 interface=ether1'
                        if 'interface=' in line:
                            m = re.search(r'interface=([^\s]+)', line)
                            if m:
                                discovered.append(m.group(1).lower())
                        elif 'name="' in line:
                            m = re.search(r'name="([^"]+)"', line)
                            if m:
                                discovered.append(m.group(1).lower())
                        else:
                            # Cisco/Juniper: first token is usually interface name
                            # e.g. 'GigabitEthernet0/0/0   192.168.99.1   YES NVRAM  up  up'
                            # e.g. 'ge-0/0/0.0   up   up   inet 192.168.99.1/24'
                            tokens = line.split()
                            if tokens:
                                candidate = tokens[0].rstrip(":,;").split(".")[0].strip()
                                if len(candidate) >= 3 and not candidate.startswith("%"):
                                    discovered.append(candidate.lower())

        return list(dict.fromkeys([d.lower() for d in discovered if d]))

    def get_running_config_command(self) -> str:
        """Command to retrieve the full active configuration."""
        return "show running-config"

    def backup_running_config(self) -> Path:
        """Fetches the complete running-configuration from the device and persists it locally."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"{self.device.host}_{timestamp}.cfg"

        logger.info(f"[*] Taking real snapshot backup of [bold cyan]{self.device.host}[/bold cyan]...")
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                config_output = conn.send_command(self.get_running_config_command())

            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(config_output)

            logger.info(f"[green]Backup snapshot successfully written to:[/green] {backup_file}")
            return backup_file
        except Exception as e:
            msg = f"Failed to perform pre-change snapshot on {self.device.host}: {e}"
            logger.error(f"[bold red]{msg}[/bold red]")
            raise DeviceConnectionError(msg) from e

    def execute_commands(self, commands: List[str]) -> str:
        """Validates and executes configuration commands on the target network device."""
        # 1. Defense-in-depth: Validate all candidate commands before connection
        sanitized_cmds = CommandValidator.validate_command_list(commands)

        logger.info(f"[*] Connecting to {self.device.host} to execute {len(sanitized_cmds)} commands...")
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                output = conn.send_config_set(sanitized_cmds)
                # Ensure device persistence if needed
                if self.device.device_type in ["cisco_ios", "cisco_xe"]:
                    conn.save_config()
                return output
        except Exception as e:
            msg = f"Execution failed on {self.device.host}: {e}"
            logger.error(f"[bold red]{msg}[/bold red]")
            raise DeviceConnectionError(msg) from e

    def run_health_check(self) -> Dict[str, str]:
        """Runs health commands to inspect operational state (for pre/post verification)."""
        results: Dict[str, str] = {}
        try:
            with ConnectHandler(**self.device.to_netmiko_dict()) as conn:
                for cmd in self.get_health_commands():
                    out = conn.send_command(cmd)
                    results[cmd] = out
            return results
        except Exception as e:
            msg = f"Failed to run health check on {self.device.host}: {e}"
            logger.error(f"[bold red]{msg}[/bold red]")
            raise DeviceConnectionError(msg) from e

    @abstractmethod
    def rollback(self, backup_reference: Optional[Path] = None) -> bool:
        """Executes a rollback to restore the device to its previous state."""
        pass
