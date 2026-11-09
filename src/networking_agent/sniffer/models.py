"""Data models for Packet Lab network capture and dissection engine."""

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProtocolLayer:
    """Represents a decoded protocol layer within a packet frame."""

    name: str
    short_name: str
    fields: dict[str, Any] = field(default_factory=dict)
    byte_start: int = 0
    byte_end: int = 0
    info: str = ""

    def summary(self) -> str:
        """Return formatted summary for tree representation."""
        if self.info:
            return f"{self.name}: {self.info}"
        return self.name


@dataclass
class CapturedPacket:
    """Represents a single captured packet frame."""

    index: int
    timestamp: float
    raw_bytes: bytes
    length: int
    captured_length: int
    source: str = "Unknown"
    destination: str = "Unknown"
    protocol: str = "RAW"
    info: str = ""
    layers: list[ProtocolLayer] = field(default_factory=list)
    expert_info: list[str] = field(default_factory=list)

    @property
    def formatted_time(self) -> str:
        """Format timestamp as HH:MM:SS.microseconds or relative seconds."""
        dt = datetime.datetime.fromtimestamp(self.timestamp, datetime.timezone.utc)
        return dt.strftime("%H:%M:%S.%f")[:12]

    def add_layer(self, layer: ProtocolLayer):
        """Append a decoded protocol layer."""
        self.layers.append(layer)


@dataclass
class CaptureFilter:
    """Filter criteria for packet display and live filtering."""

    protocol: str | None = None
    ip: str | None = None
    port: int | None = None
    free_text: str | None = None

    @property
    def is_active(self) -> bool:
        """Evaluate whether any filter rule is active."""
        return bool(self.protocol or self.ip or self.port or self.free_text)

    @property
    def source_ip(self) -> str | None:
        """Backward-compatibility alias for ip."""
        return self.ip

    @property
    def dest_ip(self) -> str | None:
        """Backward-compatibility alias for ip."""
        return self.ip

    def matches(self, packet: CapturedPacket) -> bool:
        """Evaluate whether packet satisfies filter condition."""
        if self.protocol:
            target_proto = self.protocol.strip().upper()
            packet_protos = [packet.protocol.upper()] + [layer.short_name.upper() for layer in packet.layers]
            if target_proto not in packet_protos:
                return False

        if self.ip:
            target_ip = self.ip.strip()
            if target_ip not in packet.source and target_ip not in packet.destination:
                return False

        if self.port is not None:
            port_match = False
            for layer in packet.layers:
                for k in ["Source Port", "Destination Port", "src_port", "dst_port", "Port"]:
                    if k in layer.fields and layer.fields[k] == self.port:
                        port_match = True
                        break
            if not port_match:
                return False

        if self.free_text:
            text_query = self.free_text.strip().lower()
            haystack = f"{packet.source} {packet.destination} {packet.protocol} {packet.info}".lower()
            for layer in packet.layers:
                for k, v in layer.fields.items():
                    haystack += f" {k}:{v}".lower()
            if text_query not in haystack:
                return False

        return True


@dataclass
class CaptureStats:
    """Statistical summary of a packet capture session."""

    total_packets: int = 0
    total_bytes: int = 0
    duration_seconds: float = 0.0
    protocol_counts: dict[str, int] = field(default_factory=dict)
    tcp_retransmissions: int = 0
    tcp_zero_windows: int = 0
    dns_queries: int = 0
    dns_failures: int = 0

    def update(self, packet: CapturedPacket):
        """Update metrics with packet information."""
        self.total_packets += 1
        self.total_bytes += packet.length
        proto = packet.protocol.upper()
        self.protocol_counts[proto] = self.protocol_counts.get(proto, 0) + 1

        for note in packet.expert_info:
            if "Retransmission" in note:
                self.tcp_retransmissions += 1
            if "ZeroWindow" in note or "Zero Window" in note:
                self.tcp_zero_windows += 1
            if "DNS Failure" in note or "NXDOMAIN" in note:
                self.dns_failures += 1
