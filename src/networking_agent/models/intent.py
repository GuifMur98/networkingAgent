"""Strict Pydantic models for neutral network intent representation."""

import re
from ipaddress import ip_address
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Strict regex pattern for allowable network interface identifiers across vendors:
# Disallows whitespace, newlines, semicolons, shell metacharacters, or command chaining.
INTERFACE_REGEX = re.compile(
    r"^(?:(?:GigabitEthernet|TenGigabitEthernet|TwentyFiveGigE|FortyGigabitEthernet|HundredGigE|"
    r"Ethernet|FastEthernet|Port-channel|Bundle-Ether|Vlan|Loopback|mgmt|Management)[0-9\/\.:]+|"
    r"(?:ge|xe|et|lo|ae|irb)\-[0-9\/\.:]+|"
    r"eth[0-9]+|"
    r"(?:ether|sfp|sfpplus|wlan|bridge|bonding|vlan)[0-9\-\.:]+|"
    r"sfp\-sfpplus[0-9]+)$",
    re.IGNORECASE,
)


class NetworkIntent(BaseModel):
    """Strict, sanitized schema that any AI provider is forced to output."""

    diagnosis: str = Field(
        ...,
        description="Concise technical root-cause explanation and recommendations.",
        min_length=5,
        max_length=2000,
    )
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Incident severity level.")
    requires_config_change: bool = Field(
        ..., description="True if a configuration modification is necessary to resolve the issue."
    )
    action: Literal[
        "none",
        "disable_interface",
        "enable_interface",
        "restart_interface",
        "set_interface_mtu",
        "set_interface_duplex_full",
        "reset_bgp_neighbor",
        "clear_arp_cache",
    ] = Field(..., description="Standardized neutral network action.")
    target_interface: Optional[str] = Field(
        default=None,
        description="Target network interface (e.g., GigabitEthernet1/0/1, Ethernet1/1, ge-0/0/0).",
    )
    mtu_value: Optional[int] = Field(
        default=None,
        description="Integer MTU value (typically between 68 and 9216).",
        ge=68,
        le=9216,
    )
    bgp_neighbor_ip: Optional[str] = Field(
        default=None,
        description="Valid IPv4 or IPv6 address of the BGP neighbor.",
    )

    @field_validator("target_interface")
    @classmethod
    def validate_interface_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip()
        # Strictly forbid newlines, null bytes, command injection markers
        if any(bad in v_clean for bad in ["\n", "\r", ";", "&", "|", "`", "$", " ", "\t"]):
            raise ValueError(f"Illegal character detected in interface name: '{v}'")
        if not INTERFACE_REGEX.match(v_clean):
            raise ValueError(f"Interface name '{v}' does not match standard network interface syntax.")
        return v_clean

    @field_validator("bgp_neighbor_ip")
    @classmethod
    def validate_neighbor_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Disallow newlines, whitespace, or command injection characters
        if any(bad in v for bad in ["\n", "\r", ";", "&", "|", "`", "$", " ", "\t"]):
            raise ValueError(f"Illegal character detected in BGP IP: '{v}'")
        try:
            ip_obj = ip_address(v)
            return str(ip_obj)
        except ValueError as e:
            raise ValueError(f"Invalid BGP neighbor IP address: '{v}'") from e
