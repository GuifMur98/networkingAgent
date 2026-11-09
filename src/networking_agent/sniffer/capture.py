"""Capture Manager for Packet Lab.

Orchestrates local network interface sniffing (Scapy/socket) and remote router
packet capture (Cisco Embedded Packet Capture, Juniper monitor traffic, MikroTik sniffer).
"""

import threading
import time
from pathlib import Path
from typing import Callable

from networking_agent.sniffer.models import CapturedPacket, CaptureFilter
from networking_agent.sniffer.parser import PacketParser
from networking_agent.sniffer.pcap import PcapReader, PcapWriter


class CaptureSession:
    """Manages an active or offline packet analysis session."""

    def __init__(self, max_packets: int = 5000):
        self.max_packets = max_packets
        self.packets: list[CapturedPacket] = []
        self.filtered_packets: list[CapturedPacket] = []
        self.active_filter = CaptureFilter()
        self.is_capturing: bool = False
        self._lock = threading.Lock()
        self._on_packet_callback: Callable[[CapturedPacket], None] | None = None
        self._sniffer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def set_callback(self, callback: Callable[[CapturedPacket], None]):
        """Set real-time listener for incoming packets."""
        self._on_packet_callback = callback

    def add_packet(self, raw_bytes: bytes, timestamp: float | None = None, orig_len: int = 0) -> CapturedPacket:
        """Parse raw frame and add to session."""
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            index = len(self.packets) + 1
            packet = PacketParser.parse(raw_bytes, index=index, timestamp=timestamp, orig_len=orig_len)

            if len(self.packets) >= self.max_packets:
                self.packets.pop(0)

            self.packets.append(packet)

            if self.active_filter.matches(packet):
                self.filtered_packets.append(packet)

        if self._on_packet_callback:
            try:
                self._on_packet_callback(packet)
            except Exception:
                pass

        return packet

    def clear(self):
        """Reset captured buffer."""
        with self._lock:
            self.packets.clear()
            self.filtered_packets.clear()

    def apply_filter(self, capture_filter: CaptureFilter) -> list[CapturedPacket]:
        """Filter packet list and return matched subset."""
        with self._lock:
            self.active_filter = capture_filter
            self.filtered_packets = [p for p in self.packets if capture_filter.matches(p)]
            return list(self.filtered_packets)

    def load_pcap(self, pcap_path: str | Path) -> int:
        """Load and parse packets from a .pcap file."""
        self.clear()
        reader = PcapReader(pcap_path)
        records = reader.read_packets()

        for idx, (ts, raw_data, orig_len) in enumerate(records, 1):
            pkt = PacketParser.parse(raw_data, index=idx, timestamp=ts, orig_len=orig_len)
            self.packets.append(pkt)
            if self.active_filter.matches(pkt):
                self.filtered_packets.append(pkt)

        return len(self.packets)

    def save_pcap(self, pcap_path: str | Path) -> int:
        """Export session packets to standard .pcap file."""
        with self._lock:
            pkts_to_save = list(self.packets)

        with PcapWriter(pcap_path) as writer:
            for p in pkts_to_save:
                writer.write_packet(p.raw_bytes, timestamp=p.timestamp, orig_len=p.length)

        return len(pkts_to_save)

    # ---------------- REMOTE ROUTER CAPTURE (EPC) ----------------

    @classmethod
    def generate_cisco_epc_commands(cls, interface: str = "GigabitEthernet1", buffer_size_kb: int = 2048) -> dict:
        """Generate Cisco IOS/IOS-XE Embedded Packet Capture (EPC) lifecycle commands."""
        return {
            "create": [
                f"monitor capture EPC_AGENT buffer size {buffer_size_kb} circular",
                f"monitor capture EPC_AGENT interface {interface} both",
            ],
            "start": "monitor capture EPC_AGENT start",
            "stop": "monitor capture EPC_AGENT stop",
            "export": "monitor capture EPC_AGENT export flash:agent_capture.pcap",
            "clean": "no monitor capture EPC_AGENT",
        }

    @classmethod
    def generate_juniper_capture_commands(cls, interface: str = "ge-0/0/0", count: int = 200) -> str:
        """Generate Juniper Junos packet monitoring command."""
        return f"monitor traffic interface {interface} count {count} write-file /var/tmp/junos_cap.pcap"

    @classmethod
    def generate_mikrotik_capture_commands(cls, interface: str = "ether1", file_name: str = "sniff.pcap") -> dict:
        """Generate MikroTik RouterOS packet sniffer commands."""
        return {
            "config": f"/tool sniffer set file-name={file_name} filter-interface={interface}",
            "start": "/tool sniffer start",
            "stop": "/tool sniffer stop",
        }

    # ---------------- LIVE SNIFFER (SCAPY / LOCAL) ----------------

    def start_local_capture(self, interface: str | None = None, bpf_filter: str | None = None) -> bool:
        """Start non-blocking background packet sniffing."""
        if self.is_capturing:
            return True

        self._stop_event.clear()
        self.is_capturing = True

        def _worker():
            try:
                import scapy.all as scapy

                def _scapy_callback(pkt):
                    if self._stop_event.is_set():
                        return
                    try:
                        raw = bytes(pkt)
                        self.add_packet(raw)
                    except Exception:
                        pass

                kwargs = {"prn": _scapy_callback, "store": False}
                if interface:
                    kwargs["iface"] = interface
                if bpf_filter:
                    kwargs["filter"] = bpf_filter

                # Run sniffing in thread until stop event
                sniffer = scapy.AsyncSniffer(**kwargs)
                sniffer.start()
                while not self._stop_event.is_set():
                    time.sleep(0.1)
                sniffer.stop()
            except Exception:
                self.is_capturing = False

        self._sniffer_thread = threading.Thread(target=_worker, daemon=True)
        self._sniffer_thread.start()
        return True

    def stop_capture(self):
        """Halt active live capture."""
        self.is_capturing = False
        self._stop_event.set()
        if self._sniffer_thread and self._sniffer_thread.is_alive():
            self._sniffer_thread.join(timeout=1.0)
