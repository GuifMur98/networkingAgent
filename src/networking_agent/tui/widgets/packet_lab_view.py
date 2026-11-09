"""Packet Lab TUI View - 3-Pane Interactive Packet Sniffer and Protocol Dissector.

Emulates Wireshark / Termshark in a high-performance terminal UI with Textual:
- Pane 1: Live Packet List (DataTable with color-coded protocol badges)
- Pane 2: Hierarchical Protocol Tree (Expandable/Collapsible layers and fields)
- Pane 3: Synchronized Hex Dump & ASCII Inspector with layer highlight
- AI Packet Doctor: Statistical anomaly detection and automated remediation report
"""

from pathlib import Path
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, Tree

from networking_agent.sniffer.analyzer import PacketDoctor
from networking_agent.sniffer.capture import CaptureSession
from networking_agent.sniffer.models import CapturedPacket, CaptureFilter, ProtocolLayer


class HexDumpWidget(Static):
    """Renders raw packet bytes as traditional 16-byte hex dump and ASCII columns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw_data: bytes = b""
        self.highlight_start: int = -1
        self.highlight_end: int = -1

    def set_data(self, data: bytes, highlight_range: tuple[int, int] = (-1, -1)):
        """Update displayed bytes and optional highlight byte range."""
        self.raw_data = data
        self.highlight_start, self.highlight_end = highlight_range
        self.update(self._render_hexdump())

    def _render_hexdump(self) -> Text:
        """Construct formatted Rich Text hex dump."""
        if not self.raw_data:
            return Text("Selecciona un paquete para inspeccionar su volcado hexadecimal.", style="dim italic")

        result = Text()
        total = len(self.raw_data)

        for offset in range(0, total, 16):
            chunk = self.raw_data[offset : offset + 16]

            # Offset column (e.g. 0000)
            result.append(f"{offset:04x}  ", style="bold #94a3b8")

            # Hex bytes column (split into two groups of 8)
            for i in range(16):
                byte_idx = offset + i
                if i == 8:
                    result.append(" ")

                if i < len(chunk):
                    b = chunk[i]
                    is_hl = self.highlight_start <= byte_idx < self.highlight_end
                    if is_hl:
                        result.append(f"{b:02x} ", style="bold #00e5ff on #0f172a")
                    else:
                        result.append(f"{b:02x} ", style="#f8fafc")
                else:
                    result.append("   ")

            result.append(" ")

            # ASCII column
            for i in range(len(chunk)):
                byte_idx = offset + i
                b = chunk[i]
                char = chr(b) if 32 <= b <= 126 else "."
                is_hl = self.highlight_start <= byte_idx < self.highlight_end
                if is_hl:
                    result.append(char, style="bold #00e5ff on #0f172a")
                else:
                    result.append(char, style="#38bdf8" if char != "." else "dim")

            result.append("\n")

        return result


class PacketLabView(Widget):
    """Full-featured packet capture and dissection terminal workspace."""

    class ReturnHomeRequested(Message):
        """Emitted when user requests return to dashboard."""

    class RequestAIDoctorDiagnosis(Message):
        """Emitted when user triggers AI Packet Doctor analysis."""

        def __init__(self, diagnostic_report: str):
            super().__init__()
            self.diagnostic_report = diagnostic_report

    PROTO_COLORS = {
        "TCP": "#38bdf8",
        "UDP": "#818cf8",
        "DNS": "#4ade80",
        "ICMP": "#facc15",
        "ARP": "#e879f9",
        "BGP": "#f87171",
        "OSPF": "#fb923c",
        "HTTP": "#00e5ff",
        "DHCP": "#2dd4bf",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = CaptureSession(max_packets=5000)
        self.current_packet: Optional[CapturedPacket] = None
        self._populate_demo_packets()

    def _populate_demo_packets(self):
        """Pre-populate sample protocol frames so the engineer can inspect immediately."""
        # 1. ARP Request
        arp_raw = bytes.fromhex("ffffffffffff00112233445508060001080006040001001122334455c0a80101000000000000c0a80164")
        self.session.add_packet(arp_raw, timestamp=1700000000.0)

        # 2. DNS Query (example.com)
        dns_raw = bytes.fromhex(
            "005056123456000c29abcdef08004500003b123440004011b2abc0a8016408080808"
            "d431003500270000a1b201000001000000000000076578616d706c6503636f6d0000010001"
        )
        self.session.add_packet(dns_raw, timestamp=1700000000.012)

        # 3. TCP SYN (Port 80)
        tcp_syn = bytes.fromhex(
            "005056123456000c29abcdef080045000028123540004006b2acc0a801640a000001"
            "d4320050000003e8000000005002fa4000000000"
        )
        self.session.add_packet(tcp_syn, timestamp=1700000000.024)

        # 4. TCP SYN-ACK
        tcp_synack = bytes.fromhex(
            "000c29abcdef0050561234560800450000289876400040062c6bc0a80101c0a80164"
            "0050d43200001000000003e95012721000000000"
        )
        self.session.add_packet(tcp_synack, timestamp=1700000000.026)

        # 5. ICMP Echo Request
        icmp_raw = bytes.fromhex("005056123456000c29abcdef080045000024123640004001b2b0c0a80164080808080800abcd00010001")
        self.session.add_packet(icmp_raw, timestamp=1700000000.035)

        # 6. BGP Keepalive (Port 179)
        bgp_raw = bytes.fromhex(
            "005056123456000c29abcdef080045000033123740004006b2a0c0a801640a000001"
            "d43300b300000500000001005018fa4000000000ffffffffffffffffffffffffffffffff001304"
        )
        self.session.add_packet(bgp_raw, timestamp=1700000000.050)

    def compose(self) -> ComposeResult:
        with Vertical(id="packet-lab-container"):
            # 1. Header Toolbar
            with Horizontal(id="packet-top-bar"):
                yield Label("PACKET LAB // ANALIZADOR Y CAPTURA TIPO WIRESHARK", id="packet-lab-title")
                yield Label("[CAPTURA PAUSADA - 6 tramas]", id="packet-status-label")
                yield Button("Volver (h)", id="btn-back-from-packet-lab", variant="default")

            # 2. Control & Filter Toolbar
            with Horizontal(id="packet-action-toolbar"):
                yield Button("Capturar [p]", id="btn-toggle-capture", variant="success")
                yield Button("Limpiar [c]", id="btn-clear-capture")
                yield Button("Guardar .pcap [s]", id="btn-save-pcap")
                yield Button("Cargar .pcap [o]", id="btn-load-pcap")
                yield Button("AI Packet Doctor [a]", id="btn-packet-doctor", variant="warning")

            with Horizontal(id="packet-filter-bar"):
                yield Input(
                    placeholder="Filtrar por protocolo (tcp, udp, dns, icmp, arp), IP o texto...",
                    id="packet-filter-input",
                )
                yield Button("Aplicar", id="btn-apply-filter")
                yield Button("Quitar Filtro", id="btn-reset-filter")

            # 3. Pane 1: Live Packet Table
            with Vertical(id="packet-table-wrapper"):
                yield DataTable(id="packet-table", cursor_type="row")

            # 4. Panes 2 & 3: Split Dissection Tree + Hex Dump Inspector
            with Horizontal(id="packet-detail-split"):
                with Vertical(id="packet-tree-panel"):
                    yield Label("ARBOL DE DISECCION DE PROTOCOLOS", classes="panel-sub-header")
                    yield Tree("Detalles del Paquete", id="protocol-tree")

                with Vertical(id="packet-hex-panel"):
                    yield Label("VOLCADO HEXADECIMAL Y ASCII", classes="panel-sub-header")
                    yield HexDumpWidget(id="hex-dump-viewer")

    def on_mount(self):
        """Configure table columns and populate initial rows."""
        table = self.query_one("#packet-table", DataTable)
        table.add_columns("No.", "Tiempo (UTC)", "Origen", "Destino", "Protocolo", "Longitud", "Información Resumen")
        self._refresh_table()

        if self.session.packets:
            self._display_packet(self.session.packets[0])

    def _refresh_table(self):
        """Repopulate DataTable with currently filtered packets."""
        table = self.query_one("#packet-table", DataTable)
        table.clear()

        packets_to_show = self.session.filtered_packets if self.session.filtered_packets else self.session.packets
        for p in packets_to_show:
            color = self.PROTO_COLORS.get(p.protocol, "#cbd5e1")
            proto_text = Text(f" {p.protocol} ", style=f"bold #000000 on {color}")
            info_style = "bold #ef4444" if p.expert_info else "#f8fafc"

            table.add_row(
                str(p.index),
                p.formatted_time,
                p.source,
                p.destination,
                proto_text,
                f"{p.length} B",
                Text(p.info, style=info_style),
                key=str(p.index),
            )

        status_lbl = self.query_one("#packet-status-label", Label)
        state_str = "ACTIVA" if self.session.is_capturing else "PAUSADA"
        status_lbl.update(f"[CAPTURA {state_str} - {len(packets_to_show)} tramas]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Update protocol tree and hex dump when a row is selected."""
        row_key = event.row_key.value
        try:
            pkt_index = int(row_key)
            pkt = next((p for p in self.session.packets if p.index == pkt_index), None)
            if pkt:
                self._display_packet(pkt)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        """Preview packet on cursor highlight."""
        if event.row_key:
            row_key = event.row_key.value
            try:
                pkt_index = int(row_key)
                pkt = next((p for p in self.session.packets if p.index == pkt_index), None)
                if pkt:
                    self._display_packet(pkt)
            except Exception:
                pass

    def _display_packet(self, pkt: CapturedPacket):
        """Update middle tree and right hex dump for the specified packet."""
        self.current_packet = pkt

        # Update Hex Dump
        hex_viewer = self.query_one("#hex-dump-viewer", HexDumpWidget)
        hex_viewer.set_data(pkt.raw_bytes)

        # Update Tree
        tree = self.query_one("#protocol-tree", Tree)
        tree.clear()
        tree.root.label = f"Trama #{pkt.index}: {pkt.length} bytes en cable ({pkt.captured_length} capturados)"
        tree.root.expand()

        for layer in pkt.layers:
            layer_node = tree.root.add(layer.summary(), data=layer, expand=True)
            for field_name, field_val in layer.fields.items():
                layer_node.add_leaf(f"{field_name}: {field_val}")

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Highlight corresponding layer bytes in Hex Dump when tree node is selected."""
        node = event.node
        layer: Optional[ProtocolLayer] = getattr(node, "data", None)
        if layer and self.current_packet:
            hex_viewer = self.query_one("#hex-dump-viewer", HexDumpWidget)
            hex_viewer.set_data(self.current_packet.raw_bytes, (layer.byte_start, layer.byte_end))

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button click events."""
        btn_id = event.button.id

        if btn_id == "btn-back-from-packet-lab":
            self.post_message(self.ReturnHomeRequested())

        elif btn_id == "btn-toggle-capture":
            btn = event.button
            if self.session.is_capturing:
                self.session.stop_capture()
                btn.label = "Capturar [p]"
                btn.variant = "success"
            else:
                self.session.start_local_capture()
                btn.label = "Pausar [p]"
                btn.variant = "error"
            self._refresh_table()

        elif btn_id == "btn-clear-capture":
            self.session.clear()
            self._refresh_table()
            tree = self.query_one("#protocol-tree", Tree)
            tree.clear()
            hex_viewer = self.query_one("#hex-dump-viewer", HexDumpWidget)
            hex_viewer.set_data(b"")

        elif btn_id == "btn-apply-filter":
            self._apply_current_filter()

        elif btn_id == "btn-reset-filter":
            inp = self.query_one("#packet-filter-input", Input)
            inp.value = ""
            self.session.apply_filter(CaptureFilter())
            self._refresh_table()

        elif btn_id == "btn-save-pcap":
            pcap_out = Path("packet_capture.pcap")
            saved = self.session.save_pcap(pcap_out)
            self.notify(
                f"Guardadas {saved} tramas en {pcap_out.resolve()}",
                title="PCAP Exportado",
                severity="information",
            )

        elif btn_id == "btn-load-pcap":
            pcap_in = Path("packet_capture.pcap")
            if pcap_in.exists():
                loaded = self.session.load_pcap(pcap_in)
                self._refresh_table()
                self.notify(
                    f"Cargadas {loaded} tramas desde {pcap_in.name}",
                    title="PCAP Cargado",
                    severity="information",
                )
            else:
                self.notify(
                    "No se encontró 'packet_capture.pcap' en el directorio actual.",
                    title="Archivo no encontrado",
                    severity="warning",
                )

        elif btn_id == "btn-packet-doctor":
            self._run_packet_doctor()

    def on_input_submitted(self, event: Input.Submitted):
        """Filter when Enter is pressed in input field."""
        if event.input.id == "packet-filter-input":
            self._apply_current_filter()

    def _apply_current_filter(self):
        """Read filter input and update table."""
        val = self.query_one("#packet-filter-input", Input).value.strip()
        cf = CaptureFilter()
        if val:
            val_upper = val.upper()
            if val_upper in ("TCP", "UDP", "DNS", "ICMP", "ARP", "BGP", "OSPF", "HTTP", "DHCP"):
                cf.protocol = val_upper
            else:
                cf.free_text = val

        self.session.apply_filter(cf)
        self._refresh_table()

    def _run_packet_doctor(self):
        """Invoke AI Packet Doctor and display anomaly diagnosis."""
        packets = self.session.packets
        stats, anomalies, report = PacketDoctor.analyze(packets)

        # Post message so parent app can route to AI assistant or show modal
        self.post_message(self.RequestAIDoctorDiagnosis(report))
        self.notify(
            f"Analizadas {stats.total_packets} tramas. Se detectaron {len(anomalies)} anomalías de tráfico.",
            title="Diagnóstico AI Packet Doctor",
            severity="warning" if anomalies else "information",
        )
