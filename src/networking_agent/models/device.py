"""Device inventory model with secure credential encapsulation."""

import re
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator

# Strictly matches valid IPv4, IPv6, or standard FQDN/hostnames
# Blocks path traversal (../), slashes, null bytes, command injection characters, whitespace
HOST_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\.\-:_]{0,253}$")


class DeviceInventory(BaseModel):
    """Encapsulates connection parameters for a managed network device."""

    host: str = Field(..., description="Hostname or IP address of the device")
    device_type: Literal[
        "cisco_ios",
        "cisco_xe",
        "cisco_nxos",
        "cisco_xr",
        "juniper_junos",
        "mikrotik_routeros",
        "arista_eos",
    ] = Field(..., description="Netmiko / Scrapli device platform identifier")
    username: str = Field(default="admin", description="SSH username")
    password: Optional[SecretStr] = Field(default=None, description="SSH password (encapsulated as secret)")
    secret: Optional[SecretStr] = Field(default=None, description="Enable secret for privileged EXEC mode")
    port: int = Field(default=22, description="SSH TCP port")
    key_file: Optional[str] = Field(default=None, description="Path to private SSH key file")
    use_keys: bool = Field(default=False, description="Whether to use SSH key authentication")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    system_host_keys: bool = Field(
        default=True,
        description="Whether to load system known_hosts for SSH host key verification",
    )
    ssh_strict: bool = Field(
        default=False,
        description="Whether to reject unknown SSH host keys to prevent MitM spoofing",
    )
    alt_host_keys: bool = Field(
        default=False,
        description="Whether to load an alternative known_hosts file",
    )
    alt_key_file: Optional[str] = Field(
        default=None,
        description="Path to alternative known_hosts file",
    )

    @field_validator("host")
    @classmethod
    def validate_host_security(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Device host cannot be empty.")
        if ".." in cleaned or "/" in cleaned or "\\" in cleaned or "\x00" in cleaned:
            raise ValueError("Device host contains forbidden path traversal characters.")
        if any(c in cleaned for c in [";", "&", "|", "`", "$", ">", "<", " ", "\t", "\r", "\n"]):
            raise ValueError("Device host contains illegal shell injection or whitespace characters.")
        if not HOST_REGEX.match(cleaned):
            raise ValueError(f"Device host '{v}' does not match valid IP or hostname syntax.")
        return cleaned

    def to_netmiko_dict(self) -> Dict[str, Any]:
        """Exports a dictionary compatible with Netmiko ConnectHandler."""
        data: Dict[str, Any] = {
            "device_type": self.device_type,
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "timeout": self.timeout,
            "use_keys": self.use_keys,
            "system_host_keys": self.system_host_keys,
            "ssh_strict": self.ssh_strict,
        }
        if self.alt_host_keys and self.alt_key_file:
            data["alt_host_keys"] = True
            data["alt_key_file"] = self.alt_key_file
        if self.password:
            data["password"] = self.password.get_secret_value()
        if self.secret:
            data["secret"] = self.secret.get_secret_value()
        if self.key_file:
            data["key_file"] = self.key_file
        return data

    def __repr__(self) -> str:
        return f"<DeviceInventory host='{self.host}' device_type='{self.device_type}' user='{self.username}'>"
