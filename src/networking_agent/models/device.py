"""Device inventory model with secure credential encapsulation."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, SecretStr


class DeviceInventory(BaseModel):
    """Encapsulates connection parameters for a managed network device."""

    host: str = Field(..., description="Hostname or IP address of the device")
    device_type: Literal[
        "cisco_ios",
        "cisco_xe",
        "cisco_nxos",
        "cisco_xr",
        "juniper_junos",
        "arista_eos",
    ] = Field(..., description="Netmiko / Scrapli device platform identifier")
    username: str = Field(default="admin", description="SSH username")
    password: Optional[SecretStr] = Field(default=None, description="SSH password (encapsulated as secret)")
    secret: Optional[SecretStr] = Field(default=None, description="Enable secret for privileged EXEC mode")
    port: int = Field(default=22, description="SSH TCP port")
    key_file: Optional[str] = Field(default=None, description="Path to private SSH key file")
    use_keys: bool = Field(default=False, description="Whether to use SSH key authentication")
    timeout: int = Field(default=30, description="Connection timeout in seconds")

    def to_netmiko_dict(self) -> Dict[str, Any]:
        """Exports a dictionary compatible with Netmiko ConnectHandler."""
        data: Dict[str, Any] = {
            "device_type": self.device_type,
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "timeout": self.timeout,
            "use_keys": self.use_keys,
        }
        if self.password:
            data["password"] = self.password.get_secret_value()
        if self.secret:
            data["secret"] = self.secret.get_secret_value()
        if self.key_file:
            data["key_file"] = self.key_file
        return data

    def __repr__(self) -> str:
        return f"<DeviceInventory host='{self.host}' device_type='{self.device_type}' user='{self.username}'>"
