"""Comprehensive automated test suite for Packet Lab (Wireshark-style packet capture and dissection)."""

import time
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable

from networking_agent.sniffer.analyzer import PacketDoctor
from networking_agent.sniffer.capture import CaptureSession
from networking_agent.sniffer.models import CaptureFilter
from networking_agent.sniffer.parser import PacketParser
from networking_agent.sniffer.pcap import PcapFormatError, PcapReader, PcapWriter
from networking_agent.tui.widgets.packet_lab_view import HexDumpWidget, PacketLabView


def test_pcap_reader_writer_roundtrip(tmp_path: Path):
    """Verify that PcapWriter and PcapReader preserve binary frames and microsecond timestamps."""
    pcap_file = tmp_path / "test_roundtrip.pcap"

    # Synthetic Frame: Eth + IP + UDP
    raw_packet_1 = bytes.fromhex(
        "005056123456000c29abcdef080045000020123440004011b2c5c0a801640a000001d4310035000c000064617461"
    )
    raw_packet_2 = bytes.fromhex("ffffffffffff00112233445508060001080006040001001122334455c0a80101000000000000c0a80164")
    t1 = 1700000000.123456
    t2 = 1700000001.654321

    with PcapWriter(pcap_file) as writer:
        writer.write_packet(raw_packet_1, timestamp=t1)
        writer.write_packet(raw_packet_2, timestamp=t2)

    assert pcap_file.exists()
    assert pcap_file.stat().st_size > 24

    reader = PcapReader(pcap_file)
    records = reader.read_packets()

    assert len(records) == 2
    read_ts1, read_data1, read_len1 = records[0]
    read_ts2, read_data2, read_len2 = records[1]

    assert abs(read_ts1 - t1) < 0.00001
    assert read_data1 == raw_packet_1
    assert read_len1 == len(raw_packet_1)

    assert abs(read_ts2 - t2) < 0.00001
    assert read_data2 == raw_packet_2


def test_pcap_reader_rejects_corrupted_file(tmp_path: Path):
    """Verify that PcapReader raises PcapFormatError when reading corrupted bytes."""
    corrupt_file = tmp_path / "bad.pcap"
    corrupt_file.write_bytes(b"INVALID_HEADER_DATA_1234")

    reader = PcapReader(corrupt_file)
    with pytest.raises(PcapFormatError):
        reader.read_packets()


def test_dissect_ethernet_and_arp():
    """Verify Layer 2 Ethernet and ARP frame dissection."""
    # ARP Request
    raw_arp = bytes.fromhex("ffffffffffff00112233445508060001080006040001001122334455c0a80101000000000000c0a80164")
    packet = PacketParser.parse(raw_arp, index=1, timestamp=time.time())

    assert packet.protocol == "ARP"
    assert packet.source == "192.168.1.1"
    assert packet.destination == "Broadcast"
    assert "Who has 192.168.1.100?" in packet.info
    assert any(layer.short_name == "ETH" for layer in packet.layers)
    assert any(layer.short_name == "ARP" for layer in packet.layers)


def test_dissect_ipv4_and_tcp_flags():
    """Verify IPv4 header and TCP flag decoding (SYN, ACK, Window size)."""
    # Eth (14B) + IPv4 (20B) + TCP SYN (20B)
    raw_tcp = bytes.fromhex(
        "005056123456000c29abcdef080045000028123540004006b2acc0a801640a000001d4320050000003e8000000005002fa4000000000"
    )
    packet = PacketParser.parse(raw_tcp, index=2, timestamp=time.time())

    assert packet.protocol == "TCP"
    assert packet.source == "192.168.1.100"
    assert packet.destination == "10.0.0.1"
    assert "54322 -> 80 [SYN]" in packet.info

    tcp_layer = next(layer for layer in packet.layers if layer.short_name == "TCP")
    assert tcp_layer.fields["Source Port"] == 54322
    assert tcp_layer.fields["Destination Port"] == 80
    assert tcp_layer.fields["Sequence Number"] == 1000
    assert "SYN" in str(tcp_layer.fields["Flags"])


def test_dissect_udp_and_dns_query():
    """Verify UDP and DNS query wire label decoding."""
    raw_dns = bytes.fromhex(
        "005056123456000c29abcdef08004500003b123440004011b2abc0a8016408080808"
        "d431003500270000a1b201000001000000000000076578616d706c6503636f6d0000010001"
    )
    packet = PacketParser.parse(raw_dns, index=3, timestamp=time.time())

    assert packet.protocol == "DNS"
    assert packet.source == "192.168.1.100"
    assert packet.destination == "8.8.8.8"
    assert "example.com" in packet.info

    dns_layer = next(layer for layer in packet.layers if layer.short_name == "DNS")
    assert dns_layer.fields["Query Name"] == "example.com"


def test_dissect_icmp_echo_request():
    """Verify ICMP ping request parsing."""
    raw_icmp = bytes.fromhex("005056123456000c29abcdef080045000024123640004001b2b0c0a80164080808080800abcd00010001")
    packet = PacketParser.parse(raw_icmp, index=4, timestamp=time.time())

    assert packet.protocol == "ICMP"
    assert "Echo (ping) request" in packet.info
    assert packet.source == "192.168.1.100"
    assert packet.destination == "8.8.8.8"


def test_dissect_bgp_keepalive():
    """Verify Border Gateway Protocol (BGP) message identification."""
    raw_bgp = bytes.fromhex(
        "005056123456000c29abcdef080045000033123740004006b2a0c0a801640a000001"
        "d43300b300000500000001005018fa4000000000ffffffffffffffffffffffffffffffff001304"
    )
    packet = PacketParser.parse(raw_bgp, index=5, timestamp=time.time())

    assert packet.protocol == "BGP"
    assert "KEEPALIVE Message" in packet.info
    bgp_layer = next(layer for layer in packet.layers if layer.short_name == "BGP")
    assert "KEEPALIVE" in str(bgp_layer.fields["Type"])


def test_packet_doctor_anomaly_detection():
    """Verify that PacketDoctor detects TCP retransmissions, Zero-Window, and produces diagnostics."""
    raw_tcp = (
        bytes.fromhex(
            "005056123456000c29abcdef080045000030123540004006b2a4c0a801640a000001"
            "d4320050000003e8000000005018fa4000000000"
        )
        + b"PAYLOAD_DATA"
    )

    # Frame 1: Original transmission
    p1 = PacketParser.parse(raw_tcp, index=1, timestamp=100.0)
    # Frame 2: Identical sequence + payload = Retransmission!
    p2 = PacketParser.parse(raw_tcp, index=2, timestamp=100.2)
    # Frame 3: Zero Window
    raw_zero_win = bytes.fromhex(
        "000c29abcdef0050561234560800450000289876400040062c6bc0a80101c0a80164"
        "0050d43200001000000003e95010000000000000"  # Win=0
    )
    p3 = PacketParser.parse(raw_zero_win, index=3, timestamp=100.3)

    stats, anomalies, report = PacketDoctor.analyze([p1, p2, p3])

    assert stats.total_packets == 3
    assert stats.tcp_retransmissions == 1
    assert stats.tcp_zero_windows == 1
    assert len(anomalies) >= 2

    # Check Markdown report structure
    assert "# Informe de Diagnostico: AI Packet Doctor" in report
    assert "Retransmisiones TCP" in report
    assert "Zero Window" in report


def test_capture_session_filters_and_export(tmp_path: Path):
    """Verify that CaptureSession accurately filters packets and exports to .pcap."""
    session = CaptureSession()

    # Add 1 ARP, 1 DNS, 1 TCP
    arp_raw = bytes.fromhex("ffffffffffff00112233445508060001080006040001001122334455c0a80101000000000000c0a80164")
    dns_raw = bytes.fromhex(
        "005056123456000c29abcdef08004500003b123440004011b2abc0a8016408080808d431003500270000a1b201000001000000000000076578616d706c6503636f6d0000010001"
    )
    tcp_raw = bytes.fromhex(
        "005056123456000c29abcdef080045000028123540004006b2acc0a801640a000001d4320050000003e8000000005002fa4000000000"
    )

    session.add_packet(arp_raw)
    session.add_packet(dns_raw)
    session.add_packet(tcp_raw)
    assert len(session.packets) == 3

    # Filter by protocol DNS
    dns_matched = session.apply_filter(CaptureFilter(protocol="DNS"))
    assert len(dns_matched) == 1
    assert dns_matched[0].protocol == "DNS"

    # Filter by free text IP
    ip_matched = session.apply_filter(CaptureFilter(free_text="10.0.0.1"))
    assert len(ip_matched) == 1
    assert ip_matched[0].protocol == "TCP"

    # Export to .pcap
    out_file = tmp_path / "session_export.pcap"
    saved = session.save_pcap(out_file)
    assert saved == 3
    assert out_file.exists()


def test_remote_router_capture_commands():
    """Verify Cisco EPC, Juniper, and MikroTik remote packet sniffer CLI generation."""
    cisco = CaptureSession.generate_cisco_epc_commands(interface="GigabitEthernet0/1", buffer_size_kb=4096)
    assert "monitor capture EPC_AGENT buffer size 4096 circular" in cisco["create"][0]
    assert "monitor capture EPC_AGENT interface GigabitEthernet0/1 both" in cisco["create"][1]
    assert cisco["start"] == "monitor capture EPC_AGENT start"
    assert cisco["stop"] == "monitor capture EPC_AGENT stop"

    junos = CaptureSession.generate_juniper_capture_commands(interface="ge-0/0/1", count=500)
    assert "monitor traffic interface ge-0/0/1 count 500" in junos

    tik = CaptureSession.generate_mikrotik_capture_commands(interface="ether2")
    assert "filter-interface=ether2" in tik["config"]


@pytest.mark.anyio
async def test_tui_packet_lab_view_mount_and_interaction():
    """Verify PacketLabView renders 3 panes (table, tree, hex dump) and responds to events."""

    class PacketLabTestApp(App):
        def compose(self) -> ComposeResult:
            yield PacketLabView(id="packet-lab-test")

    app = PacketLabTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        lab = app.query_one("#packet-lab-test", PacketLabView)
        assert lab is not None

        # Verify initial demo packets loaded into table
        table = app.query_one("#packet-table", DataTable)
        assert table.row_count >= 5

        # Verify Hex Dump is populated
        hex_viewer = app.query_one("#hex-dump-viewer", HexDumpWidget)
        assert len(hex_viewer.raw_data) > 0

        # Test selecting row 2
        table.move_cursor(row=1)
        await pilot.pause()
        assert lab.current_packet is not None

        # Test filter input submission
        inp = app.query_one("#packet-filter-input")
        inp.value = "dns"
        await inp.action_submit()
        await pilot.pause()
        assert table.row_count >= 1

        # Verify Back Button text
        btn_back = app.query_one("#btn-back-from-packet-lab")
        assert "Volver al Inicio (h)" in str(btn_back.label)

        # Verify Title Label
        title_lbl = app.query_one("#packet-lab-title")
        assert "ANALIZADOR DE PAQUETES" in str(title_lbl.render())
        assert "CAPTURA Y DISECCIÓN DE PAQUETES" in str(title_lbl.render())
        assert "wireshark" not in str(title_lbl.render()).lower()


def test_packet_doctor_query_ai_assistant():
    """Verify that query_ai_assistant synthesizes user inquiry and packet data."""
    raw_tcp = (
        bytes.fromhex(
            "005056123456000c29abcdef080045000030123540004006b2a4c0a801640a000001"
            "d4320050000003e8000000005018fa4000000000"
        )
        + b"PAYLOAD_DATA"
    )
    p1 = PacketParser.parse(raw_tcp, index=1, timestamp=100.0)
    p2 = PacketParser.parse(raw_tcp, index=2, timestamp=100.2)

    user_query = "Investigar causas de retransmisiones TCP y lentitud de flujo"
    report = PacketDoctor.query_ai_assistant(user_query=user_query, packets=[p1, p2])

    assert user_query in report
    assert "Diagnostico" in report or "Diagnóstico" in report
    assert "retransmisiones tcp" in report.lower()


def test_live_streaming_capture_fallback():
    """Verify CaptureSession live capture streaming adds packets in background."""
    session = CaptureSession()
    assert not session.is_capturing

    session.start_local_capture()
    assert session.is_capturing

    # Wait briefly for worker thread to generate at least 1-2 frames
    time.sleep(1.2)
    session.stop_capture()
    assert not session.is_capturing
    assert len(session.packets) >= 1

    protocols = {p.protocol for p in session.packets}
    assert len(protocols) >= 1

