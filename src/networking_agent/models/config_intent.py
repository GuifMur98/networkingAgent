"""Pydantic data models for configuration synthesis, automation templates, and batch deployment."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProtocolConfigType(str, Enum):
    """Supported network protocol and feature categories for declarative configuration."""

    BGP = "bgp"
    OSPF = "ospf"
    EIGRP = "eigrp"
    STP = "stp"
    PORT_CHANNEL = "port_channel"
    VLAN = "vlan"
    ACL = "acl"
    STATIC_ROUTE = "static_route"
    SERVICES = "services"
    CUSTOM = "custom"


class ConfigurationIntent(BaseModel):
    """Sanitized, structured schema output by the AI brain for declarative network provisioning."""

    protocol_type: ProtocolConfigType = Field(
        ...,
        description="Category of the protocol or network feature being configured.",
    )
    description: str = Field(
        ...,
        description="Human-readable summary of the configuration change.",
        min_length=5,
        max_length=2000,
    )
    target_host: Optional[str] = Field(
        default=None,
        description="IP or FQDN of the target network device.",
    )
    candidate_commands: List[str] = Field(
        ...,
        description="Vendor-specific CLI commands to inject onto the target device.",
        min_length=1,
    )
    verification_commands: List[str] = Field(
        default_factory=list,
        description="Non-intrusive read-only commands to run post-deployment to verify operational status.",
    )
    rollback_commands: List[str] = Field(
        default_factory=list,
        description="Explicit negation or inverse commands to revert this specific configuration if needed.",
    )
    safety_notes: str = Field(
        default="No critical service impact identified.",
        description="Observations regarding operational impact, maintenance window requirement, or caveats.",
    )

    @field_validator("candidate_commands", "verification_commands", "rollback_commands")
    @classmethod
    def sanitize_command_list(cls, commands: List[str]) -> List[str]:
        cleaned = []
        for cmd in commands:
            c = cmd.strip()
            if not c:
                continue
            # Forbid command chaining metacharacters
            if any(marker in c for marker in [";", "&&", "||", "`", "$("]):
                raise ValueError(f"Dangerous command chaining detected in command: '{c}'")
            cleaned.append(c)
        return cleaned


class AutomationTemplate(BaseModel):
    """Reusable configuration template with parameterized variable substitutions."""

    name: str = Field(..., description="Unique template identifier name.")
    vendor_family: str = Field(
        default="cisco_ios",
        description="Target vendor OS: cisco_ios, cisco_nxos, juniper_junos, mikrotik_routeros, generic",
    )
    description: str = Field(..., description="Functional purpose of this template.")
    template_content: str = Field(..., description="Raw configuration text or Jinja2 template structure.")
    parameters_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata dictionary defining expected variable names, types, and defaults.",
    )


class BatchDeploymentResult(BaseModel):
    """Immutable audit record representing the outcome of a multi-device batch deployment."""

    job_id: str = Field(..., description="Unique UUID identifying this deployment job.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the deployment execution.",
    )
    target_hosts: List[str] = Field(..., description="List of target device hosts included in the job.")
    device_results: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping of host -> {success: bool, applied_commands: List[str], logs: str, rollback: bool}",
    )
    summary: str = Field(..., description="Executive summary of the batch operation.")
