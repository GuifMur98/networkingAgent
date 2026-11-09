"""Native PCAP (Libpcap) binary file reader and writer for Packet Lab.

Provides zero-dependency binary serialization and deserialization compatible with
tcpdump, Zeek, and network operating system capture tools.
"""

import struct
import time
from pathlib import Path

# PCAP Magic Numbers
PCAP_MAGIC_MICROSECONDS = 0xA1B2C3D4
PCAP_MAGIC_SWAPPED = 0xD4C3B2A1
PCAP_MAGIC_NANOSECONDS = 0xA1B23C4D
LINKTYPE_ETHERNET = 1


class PcapFormatError(ValueError):
    """Raised when parsing an invalid or corrupted PCAP file."""

    pass


class PcapReader:
    """Reads raw packets and timestamps from a standard Libpcap .pcap file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.magic: int = 0
        self.version_major: int = 2
        self.version_minor: int = 4
        self.snaplen: int = 65535
        self.link_type: int = LINKTYPE_ETHERNET
        self.is_nanoseconds: bool = False
        self.endianness: str = "<"  # Little-endian default

    def read_packets(self) -> list[tuple[float, bytes, int]]:
        """Read all packet records from the PCAP file.

        Returns:
            List of tuples: (timestamp_float, raw_bytes, original_length)
        """
        packets = []
        with open(self.file_path, "rb") as f:
            header_data = f.read(24)
            if len(header_data) < 24:
                raise PcapFormatError(f"File too small for PCAP global header: {self.file_path}")

            # Detect endianness & magic
            raw_magic = struct.unpack("<I", header_data[:4])[0]
            if raw_magic in (PCAP_MAGIC_MICROSECONDS, PCAP_MAGIC_NANOSECONDS):
                self.endianness = "<"
                self.magic = raw_magic
            elif raw_magic == PCAP_MAGIC_SWAPPED:
                self.endianness = ">"
                self.magic = raw_magic
            else:
                raw_magic_be = struct.unpack(">I", header_data[:4])[0]
                if raw_magic_be in (PCAP_MAGIC_MICROSECONDS, PCAP_MAGIC_NANOSECONDS):
                    self.endianness = ">"
                    self.magic = raw_magic_be
                else:
                    raise PcapFormatError(f"Invalid PCAP magic number: 0x{raw_magic:08x}")

            self.is_nanoseconds = self.magic == PCAP_MAGIC_NANOSECONDS

            # Unpack global header: magic(4), v_maj(2), v_min(2), thiszone(4), sigfigs(4), snaplen(4), network(4)
            _, v_maj, v_min, _, _, snaplen, network = struct.unpack(f"{self.endianness}IHHIIII", header_data)
            self.version_major = v_maj
            self.version_minor = v_min
            self.snaplen = snaplen
            self.link_type = network

            # Read packet records
            while True:
                record_header = f.read(16)
                if not record_header or len(record_header) < 16:
                    break

                ts_sec, ts_usec, incl_len, orig_len = struct.unpack(f"{self.endianness}IIII", record_header)

                if incl_len > 1_000_000:
                    raise PcapFormatError(f"Corrupted packet record length: {incl_len} bytes")

                packet_bytes = f.read(incl_len)
                if len(packet_bytes) < incl_len:
                    break

                if self.is_nanoseconds:
                    ts = float(ts_sec) + (float(ts_usec) / 1_000_000_000.0)
                else:
                    ts = float(ts_sec) + (float(ts_usec) / 1_000_000.0)

                packets.append((ts, packet_bytes, orig_len))

        return packets


class PcapWriter:
    """Writes packet frames into a standard Libpcap .pcap file."""

    def __init__(self, file_path: str | Path, link_type: int = LINKTYPE_ETHERNET, snaplen: int = 65535):
        self.file_path = Path(file_path)
        self.link_type = link_type
        self.snaplen = snaplen
        self._file = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """Open file and write the standard 24-byte PCAP global header."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.file_path, "wb")
        # Global header: Magic, Version 2.4, Zone 0, Sigfigs 0, Snaplen 65535, Network LinkType
        header = struct.pack(
            "<IHHIIII",
            PCAP_MAGIC_MICROSECONDS,
            2,
            4,
            0,
            0,
            self.snaplen,
            self.link_type,
        )
        self._file.write(header)

    def write_packet(self, raw_bytes: bytes, timestamp: float | None = None, orig_len: int | None = None):
        """Append a packet frame to the PCAP file."""
        if not self._file:
            raise RuntimeError("PcapWriter is not open. Call open() or use context manager.")

        if timestamp is None:
            timestamp = time.time()

        ts_sec = int(timestamp)
        ts_usec = int((timestamp - ts_sec) * 1_000_000)

        captured_len = min(len(raw_bytes), self.snaplen)
        if orig_len is None:
            orig_len = len(raw_bytes)

        # 16-byte Packet Header
        pkt_header = struct.pack("<IIII", ts_sec, ts_usec, captured_len, orig_len)
        self._file.write(pkt_header)
        self._file.write(raw_bytes[:captured_len])

    def close(self):
        """Flush and close underlying file."""
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None
