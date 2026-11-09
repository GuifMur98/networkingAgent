"""Protocol Dissector Engine for Packet Lab.

Decodes raw network frames into structured hierarchical protocol layers:
Ethernet, 802.1Q VLAN, ARP, IPv4, IPv6, ICMP, TCP, UDP, DNS, DHCP, BGP, and OSPF.
Provides exact byte offsets for synchronized hex dump highlighting.
"""

import socket
import struct
from typing import Any

from networking_agent.sniffer.models import CapturedPacket, ProtocolLayer


def mac_to_str(raw: bytes) -> str:
    """Format 6-byte raw MAC address as colon-separated hex string."""
    return ":".join(f"{b:02x}" for b in raw)


class PacketParser:
    """High-performance multi-layer network frame dissector."""

    @classmethod
    def parse(cls, raw_bytes: bytes, index: int = 1, timestamp: float = 0.0, orig_len: int = 0) -> CapturedPacket:
        """Dissect raw frame into CapturedPacket with nested ProtocolLayers."""
        if orig_len == 0:
            orig_len = len(raw_bytes)

        packet = CapturedPacket(
            index=index,
            timestamp=timestamp,
            raw_bytes=raw_bytes,
            length=orig_len,
            captured_length=len(raw_bytes),
        )

        offset = 0
        total_len = len(raw_bytes)

        # Layer 1: Frame metadata
        frame_layer = ProtocolLayer(
            name="Frame",
            short_name="FRAME",
            fields={
                "Frame Number": index,
                "Frame Length": orig_len,
                "Capture Length": len(raw_bytes),
            },
            byte_start=0,
            byte_end=total_len,
            info=f"{orig_len} bytes on wire ({len(raw_bytes)} captured)",
        )
        packet.add_layer(frame_layer)

        if total_len < 14:
            packet.protocol = "RAW"
            packet.info = f"Malformed Short Frame ({total_len} bytes)"
            return packet

        # Layer 2: Ethernet II
        dst_mac = mac_to_str(raw_bytes[0:6])
        src_mac = mac_to_str(raw_bytes[6:12])
        ether_type = struct.unpack("!H", raw_bytes[12:14])[0]
        offset = 14

        eth_layer = ProtocolLayer(
            name="Ethernet II",
            short_name="ETH",
            fields={
                "Destination": dst_mac,
                "Source": src_mac,
                "Type": f"0x{ether_type:04x}",
            },
            byte_start=0,
            byte_end=14,
            info=f"Src: {src_mac}, Dst: {dst_mac}",
        )
        packet.add_layer(eth_layer)
        packet.source = src_mac
        packet.destination = dst_mac

        # 802.1Q VLAN Tag check
        if ether_type == 0x8100 and total_len >= offset + 4:
            vlan_tci = struct.unpack("!H", raw_bytes[offset : offset + 2])[0]
            vlan_id = vlan_tci & 0x0FFF
            vlan_pri = (vlan_tci >> 13) & 0x07
            inner_type = struct.unpack("!H", raw_bytes[offset + 2 : offset + 4])[0]

            vlan_layer = ProtocolLayer(
                name="802.1Q Virtual LAN",
                short_name="VLAN",
                fields={
                    "VLAN ID": vlan_id,
                    "Priority": vlan_pri,
                    "Inner Type": f"0x{inner_type:04x}",
                },
                byte_start=offset,
                byte_end=offset + 4,
                info=f"ID: {vlan_id}, Priority: {vlan_pri}",
            )
            packet.add_layer(vlan_layer)
            ether_type = inner_type
            offset += 4

        # Layer 3: Network Protocols
        if ether_type == 0x0800:  # IPv4
            cls._dissect_ipv4(raw_bytes, offset, packet)
        elif ether_type == 0x86DD:  # IPv6
            cls._dissect_ipv6(raw_bytes, offset, packet)
        elif ether_type == 0x0806:  # ARP
            cls._dissect_arp(raw_bytes, offset, packet)
        else:
            packet.protocol = f"0x{ether_type:04x}"
            packet.info = f"Ethernet Type 0x{ether_type:04x} Payload ({total_len - offset} bytes)"

        return packet

    @classmethod
    def _dissect_ipv4(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode IPv4 header and branch to transport layer."""
        if len(raw) < offset + 20:
            packet.protocol = "IPv4 (Truncated)"
            return

        ip_header = raw[offset : offset + 20]
        v_ihl, tos, total_len, identification, flags_frag, ttl, proto, checksum = struct.unpack(
            "!BBHHHBBH", ip_header[:12]
        )
        version = v_ihl >> 4
        ihl = (v_ihl & 0x0F) * 4
        src_ip = socket.inet_ntoa(raw[offset + 12 : offset + 16])
        dst_ip = socket.inet_ntoa(raw[offset + 16 : offset + 20])

        packet.source = src_ip
        packet.destination = dst_ip
        flags_df = bool(flags_frag & 0x4000)
        flags_mf = bool(flags_frag & 0x2000)

        ipv4_layer = ProtocolLayer(
            name="Internet Protocol Version 4",
            short_name="IPv4",
            fields={
                "Version": version,
                "Header Length": ihl,
                "Differentiated Services Field": f"0x{tos:02x}",
                "Total Length": total_len,
                "Identification": f"0x{identification:04x}",
                "Don't Fragment (DF)": flags_df,
                "More Fragments (MF)": flags_mf,
                "Time to Live (TTL)": ttl,
                "Protocol": proto,
                "Header Checksum": f"0x{checksum:04x}",
                "Source": src_ip,
                "Destination": dst_ip,
            },
            byte_start=offset,
            byte_end=offset + ihl,
            info=f"Src: {src_ip}, Dst: {dst_ip}, Proto: {proto}",
        )
        packet.add_layer(ipv4_layer)

        next_offset = offset + ihl
        # Layer 4 Transport
        if proto == 6:  # TCP
            cls._dissect_tcp(raw, next_offset, packet)
        elif proto == 17:  # UDP
            cls._dissect_udp(raw, next_offset, packet)
        elif proto == 1:  # ICMP
            cls._dissect_icmp(raw, next_offset, packet)
        elif proto == 89:  # OSPF
            cls._dissect_ospf(raw, next_offset, packet)
        else:
            packet.protocol = f"IP-Proto-{proto}"
            packet.info = f"IPv4 Protocol {proto} Data ({len(raw) - next_offset} bytes)"

    @classmethod
    def _dissect_ipv6(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode IPv6 header."""
        if len(raw) < offset + 40:
            packet.protocol = "IPv6 (Truncated)"
            return

        header = raw[offset : offset + 40]
        vtc_fl, payload_len, next_header, hop_limit = struct.unpack("!IHBB", header[:8])
        src_ip = socket.inet_ntop(socket.AF_INET6, header[8:24])
        dst_ip = socket.inet_ntop(socket.AF_INET6, header[24:40])

        packet.source = src_ip
        packet.destination = dst_ip

        ipv6_layer = ProtocolLayer(
            name="Internet Protocol Version 6",
            short_name="IPv6",
            fields={
                "Payload Length": payload_len,
                "Next Header": next_header,
                "Hop Limit": hop_limit,
                "Source": src_ip,
                "Destination": dst_ip,
            },
            byte_start=offset,
            byte_end=offset + 40,
            info=f"Src: {src_ip}, Dst: {dst_ip}, Next Header: {next_header}",
        )
        packet.add_layer(ipv6_layer)

        next_offset = offset + 40
        if next_header == 6:
            cls._dissect_tcp(raw, next_offset, packet)
        elif next_header == 17:
            cls._dissect_udp(raw, next_offset, packet)
        elif next_header == 58:  # ICMPv6
            packet.protocol = "ICMPv6"
            packet.info = f"ICMPv6 Data ({len(raw) - next_offset} bytes)"
        else:
            packet.protocol = f"IPv6-Next-{next_header}"
            packet.info = f"IPv6 Next Header {next_header}"

    @classmethod
    def _dissect_arp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode ARP packet."""
        packet.protocol = "ARP"
        if len(raw) < offset + 28:
            packet.info = "ARP (Truncated)"
            return

        hw_type, proto_type, hw_size, proto_size, opcode = struct.unpack("!HHBBH", raw[offset : offset + 8])
        sender_mac = mac_to_str(raw[offset + 8 : offset + 14])
        sender_ip = socket.inet_ntoa(raw[offset + 14 : offset + 18])
        target_mac = mac_to_str(raw[offset + 18 : offset + 24])
        target_ip = socket.inet_ntoa(raw[offset + 24 : offset + 28])

        op_name = "Request" if opcode == 1 else ("Reply" if opcode == 2 else f"Opcode {opcode}")
        info_str = f"Who has {target_ip}? Tell {sender_ip}" if opcode == 1 else f"{sender_ip} is at {sender_mac}"

        arp_layer = ProtocolLayer(
            name="Address Resolution Protocol",
            short_name="ARP",
            fields={
                "Hardware Type": hw_type,
                "Protocol Type": f"0x{proto_type:04x}",
                "Opcode": f"{op_name} ({opcode})",
                "Sender MAC": sender_mac,
                "Sender IP": sender_ip,
                "Target MAC": target_mac,
                "Target IP": target_ip,
            },
            byte_start=offset,
            byte_end=offset + 28,
            info=f"{op_name}: {info_str}",
        )
        packet.add_layer(arp_layer)
        packet.source = sender_ip
        packet.destination = target_ip if opcode == 2 else "Broadcast"
        packet.info = info_str

    @classmethod
    def _dissect_tcp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode TCP header, flags, and check for high-level L7 payload."""
        packet.protocol = "TCP"
        if len(raw) < offset + 20:
            packet.info = "TCP (Truncated Header)"
            return

        src_port, dst_port, seq, ack, offset_flags, window, checksum, urg = struct.unpack(
            "!HHIIHHHH", raw[offset : offset + 20]
        )
        tcp_header_len = ((offset_flags >> 12) & 0x0F) * 4
        flags = offset_flags & 0x0FFF

        flag_names = []
        if flags & 0x001:
            flag_names.append("FIN")
        if flags & 0x002:
            flag_names.append("SYN")
        if flags & 0x004:
            flag_names.append("RST")
        if flags & 0x008:
            flag_names.append("PSH")
        if flags & 0x010:
            flag_names.append("ACK")
        if flags & 0x020:
            flag_names.append("URG")

        flags_str = ",".join(flag_names) if flag_names else "None"
        payload_offset = offset + tcp_header_len
        payload_len = len(raw) - payload_offset

        tcp_info = f"{src_port} -> {dst_port} [{flags_str}] Seq={seq} Ack={ack} Win={window} Len={payload_len}"
        packet.info = tcp_info

        # Expert info checks
        if "RST" in flag_names:
            packet.expert_info.append("[Warning] Connection reset by peer (RST)")
        if window == 0 and "SYN" not in flag_names:
            packet.expert_info.append("[Warning] TCP Zero Window - Receiver buffer full")

        tcp_layer = ProtocolLayer(
            name="Transmission Control Protocol",
            short_name="TCP",
            fields={
                "Source Port": src_port,
                "Destination Port": dst_port,
                "Sequence Number": seq,
                "Acknowledgment Number": ack,
                "Header Length": tcp_header_len,
                "Flags": f"0x{flags:03x} ({flags_str})",
                "Window Size": window,
                "Checksum": f"0x{checksum:04x}",
                "Payload Length": payload_len,
            },
            byte_start=offset,
            byte_end=offset + tcp_header_len,
            info=tcp_info,
        )
        packet.add_layer(tcp_layer)

        # L7 Protocols over TCP
        if payload_len > 0:
            if src_port == 179 or dst_port == 179:
                cls._dissect_bgp(raw, payload_offset, packet)
            elif src_port in (80, 8080) or dst_port in (80, 8080):
                cls._dissect_http(raw, payload_offset, packet)
            elif src_port == 53 or dst_port == 53:
                cls._dissect_dns(raw, payload_offset + 2, packet)  # Skip 2-byte TCP length

    @classmethod
    def _dissect_udp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode UDP header and inspect DNS / DHCP."""
        packet.protocol = "UDP"
        if len(raw) < offset + 8:
            packet.info = "UDP (Truncated)"
            return

        src_port, dst_port, udp_len, checksum = struct.unpack("!HHHH", raw[offset : offset + 8])
        payload_offset = offset + 8
        payload_len = max(0, len(raw) - payload_offset)

        udp_info = f"{src_port} -> {dst_port} Len={udp_len - 8}"
        packet.info = udp_info

        udp_layer = ProtocolLayer(
            name="User Datagram Protocol",
            short_name="UDP",
            fields={
                "Source Port": src_port,
                "Destination Port": dst_port,
                "Length": udp_len,
                "Payload Length": payload_len,
                "Checksum": f"0x{checksum:04x}",
            },
            byte_start=offset,
            byte_end=offset + 8,
            info=udp_info,
        )
        packet.add_layer(udp_layer)

        # L7 Protocols over UDP
        if src_port == 53 or dst_port == 53:
            cls._dissect_dns(raw, payload_offset, packet)
        elif (src_port in (67, 68)) and (dst_port in (67, 68)):
            cls._dissect_dhcp(raw, payload_offset, packet)

    @classmethod
    def _dissect_icmp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode ICMP header."""
        packet.protocol = "ICMP"
        if len(raw) < offset + 4:
            packet.info = "ICMP (Truncated)"
            return

        icmp_type, icmp_code, checksum = struct.unpack("!BBH", raw[offset : offset + 4])
        type_names = {
            0: "Echo (ping) reply",
            3: "Destination unreachable",
            5: "Redirect",
            8: "Echo (ping) request",
            11: "Time-to-live exceeded",
        }
        type_str = type_names.get(icmp_type, f"Type {icmp_type}")

        extra_fields: dict[str, Any] = {}
        info_extra = ""
        if icmp_type in (0, 8) and len(raw) >= offset + 8:
            ident, seq = struct.unpack("!HH", raw[offset + 4 : offset + 8])
            extra_fields["Identifier"] = ident
            extra_fields["Sequence Number"] = seq
            info_extra = f" id=0x{ident:04x}, seq={seq}"

        info_str = f"{type_str} (code={icmp_code}){info_extra}"
        packet.info = info_str

        icmp_layer = ProtocolLayer(
            name="Internet Control Message Protocol",
            short_name="ICMP",
            fields={
                "Type": f"{icmp_type} ({type_str})",
                "Code": icmp_code,
                "Checksum": f"0x{checksum:04x}",
                **extra_fields,
            },
            byte_start=offset,
            byte_end=offset + 8 if extra_fields else offset + 4,
            info=info_str,
        )
        packet.add_layer(icmp_layer)

    @classmethod
    def _dissect_dns(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode DNS message."""
        if len(raw) < offset + 12:
            return

        tx_id, flags, qd_count, an_count, ns_count, ar_count = struct.unpack("!HHHHHH", raw[offset : offset + 12])
        is_response = bool(flags & 0x8000)
        rcode = flags & 0x000F

        # Parse first query name if present
        qname, next_off = cls._extract_dns_name(raw, offset + 12)

        direction = "Standard query response" if is_response else "Standard query"
        rcode_names = {0: "No error", 2: "Server failure", 3: "No such name (NXDOMAIN)"}
        rcode_str = rcode_names.get(rcode, f"RCODE {rcode}")

        if is_response and rcode != 0:
            packet.expert_info.append(f"[Warning] DNS Failure: {rcode_str}")

        info_str = f"{direction} 0x{tx_id:04x} {qname}" if qname else f"{direction} 0x{tx_id:04x}"
        if is_response and rcode != 0:
            info_str += f" ({rcode_str})"

        packet.protocol = "DNS"
        packet.info = info_str

        dns_layer = ProtocolLayer(
            name="Domain Name System",
            short_name="DNS",
            fields={
                "Transaction ID": f"0x{tx_id:04x}",
                "Flags": f"0x{flags:04x} (Response: {is_response}, RCODE: {rcode})",
                "Questions": qd_count,
                "Answer RRs": an_count,
                "Query Name": qname,
                "Response Status": rcode_str,
            },
            byte_start=offset,
            byte_end=len(raw),
            info=info_str,
        )
        packet.add_layer(dns_layer)

    @classmethod
    def _extract_dns_name(cls, raw: bytes, offset: int) -> tuple[str, int]:
        """Extract dot-separated DNS name from wire labels."""
        labels = []
        curr = offset
        while curr < len(raw):
            length = raw[curr]
            if length == 0:
                curr += 1
                break
            if length >= 0xC0:  # Pointer
                curr += 2
                break
            curr += 1
            if curr + length <= len(raw):
                labels.append(raw[curr : curr + length].decode("ascii", errors="replace"))
                curr += length
            else:
                break
        return ".".join(labels), curr

    @classmethod
    def _dissect_dhcp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode DHCP / BOOTP packet."""
        if len(raw) < offset + 44:
            return

        op, htype, hlen, hops, xid = struct.unpack("!BBBBI", raw[offset : offset + 8])
        ciaddr = socket.inet_ntoa(raw[offset + 12 : offset + 16])
        yiaddr = socket.inet_ntoa(raw[offset + 16 : offset + 20])
        chaddr = mac_to_str(raw[offset + 28 : offset + 34])

        op_name = "BOOTREQUEST" if op == 1 else "BOOTREPLY"
        packet.protocol = "DHCP"
        info_str = f"{op_name} XID: 0x{xid:08x} Client: {chaddr}"
        packet.info = info_str

        dhcp_layer = ProtocolLayer(
            name="Dynamic Host Configuration Protocol",
            short_name="DHCP",
            fields={
                "Message Type": f"{op} ({op_name})",
                "Transaction ID": f"0x{xid:08x}",
                "Client IP": ciaddr,
                "Your (client) IP": yiaddr,
                "Client MAC": chaddr,
            },
            byte_start=offset,
            byte_end=len(raw),
            info=info_str,
        )
        packet.add_layer(dhcp_layer)

    @classmethod
    def _dissect_bgp(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode BGP protocol header."""
        if len(raw) < offset + 19:
            return

        marker = raw[offset : offset + 16]
        if marker == b"\xff" * 16:
            bgp_len, bgp_type = struct.unpack("!HB", raw[offset + 16 : offset + 19])
            type_names = {
                1: "OPEN",
                2: "UPDATE",
                3: "NOTIFICATION",
                4: "KEEPALIVE",
                5: "ROUTE-REFRESH",
            }
            type_str = type_names.get(bgp_type, f"Type {bgp_type}")
            packet.protocol = "BGP"
            info_str = f"{type_str} Message (Len={bgp_len})"
            packet.info = info_str

            bgp_layer = ProtocolLayer(
                name="Border Gateway Protocol",
                short_name="BGP",
                fields={
                    "Type": f"{type_str} ({bgp_type})",
                    "Length": bgp_len,
                },
                byte_start=offset,
                byte_end=offset + bgp_len,
                info=info_str,
            )
            packet.add_layer(bgp_layer)

    @classmethod
    def _dissect_ospf(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode OSPF protocol header."""
        if len(raw) < offset + 16:
            return

        version, ospf_type, ospf_len = struct.unpack("!BBH", raw[offset : offset + 4])
        router_id = socket.inet_ntoa(raw[offset + 4 : offset + 8])
        area_id = socket.inet_ntoa(raw[offset + 8 : offset + 12])

        type_names = {
            1: "Hello",
            2: "Database Description (DBD)",
            3: "Link State Request (LSR)",
            4: "Link State Update (LSU)",
            5: "Link State Ack (LSAck)",
        }
        type_str = type_names.get(ospf_type, f"Type {ospf_type}")
        packet.protocol = "OSPF"
        info_str = f"OSPFv{version} {type_str} from {router_id} (Area {area_id})"
        packet.info = info_str

        ospf_layer = ProtocolLayer(
            name=f"Open Shortest Path First v{version}",
            short_name="OSPF",
            fields={
                "Version": version,
                "Type": f"{type_str} ({ospf_type})",
                "Packet Length": ospf_len,
                "Source Router ID": router_id,
                "Area ID": area_id,
            },
            byte_start=offset,
            byte_end=offset + ospf_len,
            info=info_str,
        )
        packet.add_layer(ospf_layer)

    @classmethod
    def _dissect_http(cls, raw: bytes, offset: int, packet: CapturedPacket):
        """Decode HTTP request or response lines."""
        try:
            payload = raw[offset:].decode("utf-8", errors="ignore")
            lines = payload.split("\r\n")
            if lines and lines[0]:
                first_line = lines[0]
                methods = ("GET ", "POST ", "PUT ", "DELETE ", "HEAD ", "OPTIONS ", "HTTP/")
                if any(first_line.startswith(m) for m in methods):
                    packet.protocol = "HTTP"
                    packet.info = first_line[:80]

                    http_layer = ProtocolLayer(
                        name="Hypertext Transfer Protocol",
                        short_name="HTTP",
                        fields={"Header": first_line},
                        byte_start=offset,
                        byte_end=len(raw),
                        info=first_line,
                    )
                    packet.add_layer(http_layer)
        except Exception:
            pass
