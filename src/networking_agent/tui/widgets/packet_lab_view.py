"""Analizador de Paquetes TUI View - 3 Paneles Interactivos de Captura y Disección.

Disección e inspección profunda de tráfico en terminal de alta fidelidad:
- Panel 1: Lista de Paquetes en Vivo (DataTable con distintivos de protocolo por color)
- Panel 2: Árbol Jerárquico de Disección (Capas L2-L7 y campos decodificados)
- Panel 3: Volcado Hexadecimal y ASCII Sincronizado con resaltado de capa
- Analizador IA de Tráfico: Diagnóstico contextual con modelos LLM y remediación autónoma
"""

from pathlib import Path
from typing import Optional

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, Tree
from textual.widgets._data_table import DuplicateKey
from textual.widgets.data_table import RowKey

from networking_agent.sniffer.analyzer import PacketDoctor
from networking_agent.sniffer.capture import CaptureSession
from networking_agent.sniffer.models import CapturedPacket, CaptureFilter, ProtocolLayer
from networking_agent.tui.modals.packet_doctor_modal import PacketDoctorModal
from networking_agent.tui.modals.packet_query_modal import PacketAIQueryModal
from networking_agent.tui.modals.pcap_file_modal import LoadPcapModal, SavePcapModal


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
        self._last_rendered_index: int = 0
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
        with VerticalScroll(id="packet-lab-container"):
            # 1. Header Toolbar
            with Horizontal(id="packet-top-bar"):
                yield Label("ANALIZADOR DE PAQUETES // CAPTURA Y DISECCIÓN DE PAQUETES", id="packet-lab-title")
                yield Label("[CAPTURA PAUSADA - 6 tramas]", id="packet-status-label")
                yield Button("Volver al Inicio (h)", id="btn-back-from-packet-lab", variant="default")

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
        """Configure table columns, populate initial rows, and set up live polling timer."""
        table = self.query_one("#packet-table", DataTable)
        table.add_columns("No.", "Tiempo (UTC)", "Origen", "Destino", "Protocolo", "Longitud", "Información Resumen")
        self._refresh_table()

        if self.session.packets:
            self._display_packet(self.session.packets[0])

        # Timer for live capture updates (polling every 350ms)
        self._live_timer = self.set_interval(0.35, self._on_live_capture_poll, pause=True)

    def _on_live_capture_poll(self) -> None:
        """Poll capture session and stream incoming frames to DataTable in real time."""
        if not self.session.is_capturing:
            return

        new_pkts = self.session.get_packets_since(self._last_rendered_index)
        if not new_pkts:
            return

        table = self.query_one("#packet-table", DataTable)
        cf = self.session.active_filter
        has_filter = bool(cf and (cf.protocol or cf.ip or cf.port or cf.free_text))

        added_any = False
        for p in new_pkts:
            self._last_rendered_index = max(self._last_rendered_index, p.index)

            if has_filter and not cf.matches(p):
                continue

            color = self.PROTO_COLORS.get(p.protocol, "#cbd5e1")
            proto_text = Text(f" {p.protocol} ", style=f"bold #000000 on {color}")
            info_style = "bold #ef4444" if p.expert_info else "#f8fafc"

            row_key = str(p.index)
            if RowKey(row_key) in table._row_locations:
                continue

            try:
                table.add_row(
                    str(p.index),
                    p.formatted_time,
                    p.source,
                    p.destination,
                    proto_text,
                    f"{p.length} B",
                    Text(p.info, style=info_style),
                    key=row_key,
                )
                added_any = True
            except DuplicateKey:
                continue

        if added_any:
            try:
                table.scroll_end(animate=False)
            except Exception:
                pass

        total_pkts = len(self.session.packets)
        status_lbl = self.query_one("#packet-status-label", Label)
        status_lbl.update(f"[CAPTURA ACTIVA - {total_pkts} tramas]")

        if self.current_packet is None and self.session.packets:
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

            row_key = str(p.index)
            if RowKey(row_key) in table._row_locations:
                continue

            try:
                table.add_row(
                    str(p.index),
                    p.formatted_time,
                    p.source,
                    p.destination,
                    proto_text,
                    f"{p.length} B",
                    Text(p.info, style=info_style),
                    key=row_key,
                )
            except DuplicateKey:
                continue

        self._last_rendered_index = max((p.index for p in self.session.packets), default=0)
        status_lbl = self.query_one("#packet-status-label", Label)
        state_str = "ACTIVA" if self.session.is_capturing else "PAUSADA"
        status_lbl.update(f"[CAPTURA {state_str} - {len(packets_to_show)} tramas]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Update protocol tree and hex dump when a row is selected."""
        row_key = event.row_key.value
        try:
            pkt_index = int(row_key)
            pkt = self.session.get_packet_by_index(pkt_index)
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
                pkt = self.session.get_packet_by_index(pkt_index)
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
                if hasattr(self, "_live_timer"):
                    self._live_timer.pause()
                status_lbl = self.query_one("#packet-status-label", Label)
                status_lbl.update(f"[CAPTURA PAUSADA - {len(self.session.packets)} tramas]")
            else:
                self.session.start_local_capture()
                btn.label = "Pausar [p]"
                btn.variant = "error"
                if hasattr(self, "_live_timer"):
                    self._live_timer.resume()
                status_lbl = self.query_one("#packet-status-label", Label)
                status_lbl.update(f"[CAPTURA ACTIVA - {len(self.session.packets)} tramas]")

        elif btn_id == "btn-clear-capture":
            self.session.clear()
            self._last_rendered_index = 0
            self.current_packet = None
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
            self.app.push_screen(
                SavePcapModal(default_path="captura_red.pcap"),
                callback=self._on_save_pcap_path,
            )

        elif btn_id == "btn-load-pcap":
            self.app.push_screen(
                LoadPcapModal(default_path="captura_red.pcap"),
                callback=self._on_load_pcap_path,
            )

        elif btn_id == "btn-packet-doctor":
            self.app.push_screen(
                PacketAIQueryModal(packet_count=len(self.session.packets)),
                callback=self._on_ai_query_submitted,
            )

    def _on_save_pcap_path(self, target_path: Optional[Path]) -> None:
        """Handle path selected in SavePcapModal."""
        if not target_path:
            return
        try:
            saved = self.session.save_pcap(target_path)
            self.notify(
                f"Se guardaron exitosamente {saved} tramas en: {target_path}",
                title="Captura PCAP Exportada",
                severity="information",
            )
        except Exception as e:
            self.notify(
                f"Error al guardar archivo PCAP: {e}",
                title="Error de Exportación",
                severity="error",
            )

    def _on_load_pcap_path(self, target_path: Optional[Path]) -> None:
        """Handle path selected in LoadPcapModal."""
        if not target_path:
            return
        if not target_path.exists():
            self.notify(
                f"No se encontró el archivo '{target_path}'. Verifique la ruta especificada.",
                title="Archivo no encontrado",
                severity="warning",
            )
            return

        try:
            loaded = self.session.load_pcap(target_path)
            self._last_rendered_index = max((p.index for p in self.session.packets), default=0)
            self._refresh_table()
            if self.session.packets:
                self._display_packet(self.session.packets[0])
            self.notify(
                f"Se cargaron exitosamente {loaded} tramas desde {target_path.name}",
                title="PCAP Importado",
                severity="information",
            )
        except Exception as e:
            self.notify(
                f"Error al abrir archivo PCAP: {e}",
                title="Error de Lectura",
                severity="error",
            )

    def _on_ai_query_submitted(self, query: Optional[str]) -> None:
        """Handle query submitted in PacketAIQueryModal and trigger AI diagnosis."""
        if not query:
            return

        self.notify(
            f"Analizando captura con IA: '{query[:45]}...'...",
            title="Diagnóstico AI en Proceso",
            severity="information",
        )
        self._analyze_packets_with_ai(query)

    @work(thread=True)
    def _analyze_packets_with_ai(self, query: str) -> None:
        """Execute AI analysis in background worker thread and push diagnostic modal."""
        packets = list(self.session.packets)
        report = PacketDoctor.query_ai_assistant(user_query=query, packets=packets)

        def _show_modal():
            self.app.push_screen(PacketDoctorModal(report))

        self.app.call_from_thread(_show_modal)

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
