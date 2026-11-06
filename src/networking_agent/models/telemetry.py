"""Telemetry and event ingestion models."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

MAX_TELEMETRY_LENGTH = 30000


class TelemetryEvent(BaseModel):
    """Represents an incoming syslog, telemetry metric, or alert event."""

    raw_text: str = Field(
        ...,
        max_length=MAX_TELEMETRY_LENGTH,
        description="Unparsed log message or telemetry notification",
    )
    source_host: Optional[str] = Field(default=None, description="Reported device host or IP")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event detection timestamp",
    )
    facility: Optional[str] = Field(default=None, description="Syslog facility (e.g. OSPF, BGP, LINK)")
    severity: Optional[int] = Field(default=None, description="RFC 5424 severity code (0-7)")

    @field_validator("raw_text")
    @classmethod
    def sanitize_raw_text(cls, v: str) -> str:
        v_clean = v.replace("\x00", "")
        if not v_clean.strip():
            raise ValueError("Telemetry raw_text cannot be empty.")
        return v_clean
