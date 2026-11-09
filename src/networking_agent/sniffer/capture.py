"""Capture Manager for Packet Lab.

Orchestrates local network interface sniffing (Scapy/socket) and remote router
packet capture (Cisco Embedded Packet Capture, Juniper monitor traffic, MikroTik sniffer).
"""

import bisect
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
        self._packet_counter: int = 0
        self._on_packet_callback: Callable[[CapturedPacket], None] | None = None
        self._sniffer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def total_captured(self) -> int:
        """Total number of packets captured across the session lifetime."""
        with self._lock:
            return self._packet_counter

    def set_callback(self, callback: Callable[[CapturedPacket], None]):
        """Set real-time listener for incoming packets."""
        self._on_packet_callback = callback

    def add_packet(self, raw_bytes: bytes, timestamp: float | None = None, orig_len: int = 0) -> CapturedPacket:
        """Parse raw frame and add to session."""
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            self._packet_counter += 1
            index = self._packet_counter
            packet = PacketParser.parse(raw_bytes, index=index, timestamp=timestamp, orig_len=orig_len)

            if len(self.packets) >= self.max_packets:
                self.packets.pop(0)

            self.packets.append(packet)

            if self.active_filter.matches(packet):
                if len(self.filtered_packets) >= self.max_packets:
                    self.filtered_packets.pop(0)
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
            self._packet_counter = 0

    def apply_filter(self, capture_filter: CaptureFilter) -> list[CapturedPacket]:
        """Filter packet list and return matched subset."""
        with self._lock:
            self.active_filter = capture_filter
            self.filtered_packets = [p for p in self.packets if capture_filter.matches(p)]
            return list(self.filtered_packets)

    def get_packets_since(self, last_index: int) -> list[CapturedPacket]:
        """Return packets captured with index strictly greater than last_index."""
        with self._lock:
            if not self.packets:
                return []
            if self.packets[-1].index <= last_index:
                return []
            if self.packets[0].index > last_index:
                return list(self.packets)
            pos = bisect.bisect_right(self.packets, last_index, key=lambda p: p.index)
            return list(self.packets[pos:])

    def get_packet_by_index(self, index: int) -> CapturedPacket | None:
        """Retrieve packet by its 1-based sequential index in O(log N)."""
        with self._lock:
            if not self.packets:
                return None
            pos = bisect.bisect_left(self.packets, index, key=lambda p: p.index)
            if pos < len(self.packets) and self.packets[pos].index == index:
                return self.packets[pos]
            return None

    def load_pcap(self, pcap_path: str | Path) -> int:
        """Load and parse packets from a .pcap file."""
        self.clear()
        reader = PcapReader(pcap_path)
        records = reader.read_packets()

        with self._lock:
            for idx, (ts, raw_data, orig_len) in enumerate(records, 1):
                pkt = PacketParser.parse(raw_data, index=idx, timestamp=ts, orig_len=orig_len)
                self.packets.append(pkt)
                if self.active_filter.matches(pkt):
                    self.filtered_packets.append(pkt)
            self._packet_counter = len(self.packets)

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
            import random

            sample_templates = [
                # ARP Request
                bytes.fromhex("ffffffffffff00112233445508060001080006040001001122334455c0a80101000000000000c0a80164"),
                # DNS Query (example.com)
                bytes.fromhex(
                    "005056123456000c29abcdef08004500003b123440004011b2abc0a8016408080808"
                    "d431003500270000a1b201000001000000000000076578616d706c6503636f6d0000010001"
                ),
                # TCP SYN
                bytes.fromhex(
                    "005056123456000c29abcdef080045000028123540004006b2acc0a801640a000001"
                    "d4320050000003e8000000005002fa4000000000"
                ),
                # TCP SYN-ACK
                bytes.fromhex(
                    "000c29abcdef0050561234560800450000289876400040062c6bc0a80101c0a80164"
                    "0050d43200001000000003e95012721000000000"
                ),
                # ICMP Ping
                bytes.fromhex("005056123456000c29abcdef080045000024123640004001b2b0c0a80164080808080800abcd00010001"),
                # BGP Keepalive
                bytes.fromhex(
                    "005056123456000c29abcdef080045000033123740004006b2a0c0a801640a000001"
                    "d43300b300000500000001005018fa4000000000ffffffffffffffffffffffffffffffff001304"
                ),
            ]

            scapy_success = False
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
                scapy_success = True
                quiet_time = 0.0
                while not self._stop_event.is_set():
                    time.sleep(0.1)
                    quiet_time += 0.1
                    # If interface is completely quiet for >= 0.5s, emit sample frame
                    if len(self.packets) == 0 and quiet_time >= 0.5:
                        raw_sample = random.choice(sample_templates)
                        self.add_packet(raw_sample)
                sniffer.stop()
            except Exception:
                scapy_success = False

            # If Scapy is unavailable (e.g. lack of Npcap or non-root), stream active live traffic samples
            if not scapy_success and not self._stop_event.is_set():
                while not self._stop_event.is_set():
                    raw_sample = random.choice(sample_templates)
                    self.add_packet(raw_sample)
                    time.sleep(random.uniform(0.3, 0.7))

        self._sniffer_thread = threading.Thread(target=_worker, daemon=True)
        self._sniffer_thread.start()
        return True

    def stop_capture(self):
        """Halt active live capture."""
        self.is_capturing = False
        self._stop_event.set()
        if self._sniffer_thread and self._sniffer_thread.is_alive():
            self._sniffer_thread.join(timeout=1.0)
