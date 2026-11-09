"""AI Packet Doctor & Statistical Anomaly Analyzer for Packet Lab.

Analyzes capture sessions for TCP performance degradation, retransmissions,
window exhaustion, MTU blackholes, DNS failures, and prepares automated root cause
diagnostics with remediation recommendations.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from networking_agent.sniffer.models import CapturedPacket, CaptureStats


@dataclass
class PacketAnomaly:
    """Represents a detected network anomaly or performance degradation."""

    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str
    description: str
    packet_indices: list[int] = field(default_factory=list)
    recommendation: str = ""


class PacketDoctor:
    """Expert anomaly detection and diagnostic analyzer for captured traffic."""

    @classmethod
    def analyze(cls, packets: list[CapturedPacket]) -> tuple[CaptureStats, list[PacketAnomaly], str]:
        """Perform deep analysis of packet stream.

        Returns:
            Tuple of (CaptureStats, list of PacketAnomaly, markdown_diagnostic_report)
        """
        stats = CaptureStats()
        anomalies: list[PacketAnomaly] = []

        if not packets:
            return stats, anomalies, "No se registraron paquetes en la sesión para analizar."

        # Calculate timing
        first_ts = packets[0].timestamp
        last_ts = packets[-1].timestamp
        stats.duration_seconds = max(0.001, last_ts - first_ts)

        # Tracking state
        tcp_flows: dict[tuple, list[CapturedPacket]] = defaultdict(list)
        tcp_seq_seen: dict[tuple, dict[int, int]] = defaultdict(dict)  # (flow_key) -> {seq: count}
        dns_failures: list[CapturedPacket] = []
        tcp_resets: list[CapturedPacket] = []
        zero_windows: list[CapturedPacket] = []
        retransmissions: list[CapturedPacket] = []
        mtu_drops: list[CapturedPacket] = []

        for p in packets:
            stats.update(p)

            # Analyze TCP
            if p.protocol == "TCP" or any(layer.short_name == "TCP" for layer in p.layers):
                tcp_layer = next((layer for layer in p.layers if layer.short_name == "TCP"), None)
                if tcp_layer:
                    src_port = tcp_layer.fields.get("Source Port")
                    dst_port = tcp_layer.fields.get("Destination Port")
                    seq = tcp_layer.fields.get("Sequence Number", 0)
                    window = tcp_layer.fields.get("Window Size", 0)
                    flags_str = str(tcp_layer.fields.get("Flags", ""))
                    payload_len = tcp_layer.fields.get("Payload Length", 0)

                    flow_key = (p.source, p.destination, src_port, dst_port)
                    tcp_flows[flow_key].append(p)

                    # Check Zero Window
                    if window == 0 and "SYN" not in flags_str:
                        zero_windows.append(p)

                    # Check RST
                    if "RST" in flags_str:
                        tcp_resets.append(p)

                    # Detect Retransmissions (same seq with payload seen before in flow)
                    if payload_len > 0:
                        flow_seqs = tcp_seq_seen[flow_key]
                        if seq in flow_seqs:
                            retransmissions.append(p)
                            p.expert_info.append(f"[Warning] TCP Retransmission (Seq={seq})")
                        else:
                            flow_seqs[seq] = p.index

            # Analyze ICMP (MTU Discovery)
            if p.protocol == "ICMP":
                icmp_layer = next((layer for layer in p.layers if layer.short_name == "ICMP"), None)
                if icmp_layer:
                    icmp_type = icmp_layer.fields.get("Type", "")
                    icmp_code = icmp_layer.fields.get("Code", 0)
                    if "Destination unreachable" in str(icmp_type) and icmp_code == 4:
                        mtu_drops.append(p)

            # Analyze DNS
            if p.protocol == "DNS" or any(layer.short_name == "DNS" for layer in p.layers):
                stats.dns_queries += 1
                dns_layer = next((layer for layer in p.layers if layer.short_name == "DNS"), None)
                if dns_layer:
                    status = dns_layer.fields.get("Response Status", "")
                    if status and status != "No error":
                        dns_failures.append(p)

        stats.tcp_retransmissions = len(retransmissions)
        stats.tcp_zero_windows = len(zero_windows)
        stats.dns_failures = len(dns_failures)

        # ---------------- EVALUATE ANOMALIES ----------------

        # 1. TCP Retransmissions
        if len(retransmissions) > 0:
            retrans_rate = (len(retransmissions) / max(1, stats.total_packets)) * 100
            sev = "HIGH" if retrans_rate > 5.0 else "MEDIUM"
            anomalies.append(
                PacketAnomaly(
                    category="Transporte (TCP)",
                    severity=sev,
                    title=f"Alta Tasa de Retransmisiones TCP ({retrans_rate:.1f}%)",
                    description=(
                        f"Se detectaron {len(retransmissions)} tramas de retransmisión TCP en el flujo capturado. "
                        "Indica pérdida severa de paquetes en la ruta o congestión de buffer en interfaces intermedias."
                    ),
                    packet_indices=[p.index for p in retransmissions[:5]],
                    recommendation=(
                        "Inspeccionar contadores de interfaz (CRC errors, input drops) en routers intermedios "
                        "y verificar configuración de dúplex o atenuación física de enlaces WAN."
                    ),
                )
            )

        # 2. TCP Zero Window (Buffer Exhaustion)
        if len(zero_windows) > 0:
            anomalies.append(
                PacketAnomaly(
                    category="Rendimiento de Aplicación",
                    severity="HIGH",
                    title=f"Bloqueo de Control de Flujo: TCP Zero Window ({len(zero_windows)} eventos)",
                    description=(
                        "El receptor ha anunciado un tamaño de ventana 0 (Window=0), notificando que sus buffers de "
                        "recepción en socket están totalmente colapsados e impidiendo la transmisión de datos."
                    ),
                    packet_indices=[p.index for p in zero_windows[:5]],
                    recommendation=(
                        "Revisar saturación de CPU y consumo de memoria en el servidor destino; "
                        "verificar si el proceso de aplicación está bloqueado en E/S de base de datos."
                    ),
                )
            )

        # 3. Connection Resets (RST)
        if len(tcp_resets) > 2:
            anomalies.append(
                PacketAnomaly(
                    category="Conectividad / Seguridad",
                    severity="MEDIUM",
                    title=f"Cierres Abruptos de Conexión: TCP RST ({len(tcp_resets)} tramas)",
                    description=(
                        f"Se registraron {len(tcp_resets)} tramas TCP RST. Esto ocurre cuando un puerto destino "
                        "se encuentra cerrado o un firewall estatal (Stateful) aborta la conexión."
                    ),
                    packet_indices=[p.index for p in tcp_resets[:5]],
                    recommendation=(
                        "Verificar que el servicio en el host destino esté escuchando en el puerto requerido "
                        "y comprobar tablas de sesión NAT/Firewall por expiración de timeouts (Idle Timeouts)."
                    ),
                )
            )

        # 4. Path MTU Blackhole (ICMP Type 3 Code 4)
        if len(mtu_drops) > 0:
            anomalies.append(
                PacketAnomaly(
                    category="Enrutamiento / MTU",
                    severity="CRITICAL",
                    title=f"Problema de Path MTU Discovery ({len(mtu_drops)} mensajes ICMP)",
                    description=(
                        "Se recibieron mensajes ICMP 'Fragmentation Needed' con flag Don't Fragment (DF) activo. "
                        "Existe una discrepancia de MTU entre la LAN y los túneles WAN (VPN, GRE o PPPoE)."
                    ),
                    packet_indices=[p.index for p in mtu_drops[:5]],
                    recommendation=(
                        "Configurar TCP MSS Clamping en el router perimetral: 'ip tcp adjust-mss 1452' "
                        "o verificar que el firewall no esté bloqueando ICMP Type 3 Code 4."
                    ),
                )
            )

        # 5. DNS Resolution Failures
        if len(dns_failures) > 0:
            anomalies.append(
                PacketAnomaly(
                    category="Servicios de Red (DNS)",
                    severity="HIGH" if len(dns_failures) > 3 else "MEDIUM",
                    title=f"Fallos de Resolución de Nombres DNS ({len(dns_failures)} respuestas fallidas)",
                    description=(
                        f"Se capturaron {len(dns_failures)} respuestas DNS con error (NXDOMAIN / SERVFAIL). "
                        "Los clientes consultan registros inexistentes o el servidor DNS primario no responde."
                    ),
                    packet_indices=[p.index for p in dns_failures[:5]],
                    recommendation=(
                        "Comprobar reenviadores (forwarders) del servidor DNS y verificar si existe "
                        "un error tipográfico en el FQDN consultado por la aplicación."
                    ),
                )
            )

        # Build Markdown Diagnostic Report
        report = cls._generate_markdown_report(stats, anomalies)
        return stats, anomalies, report

    @classmethod
    def _generate_markdown_report(cls, stats: CaptureStats, anomalies: list[PacketAnomaly]) -> str:
        """Construct structured Markdown diagnosis for display in TUI and export."""
        pps = stats.total_packets / stats.duration_seconds
        kbps = (stats.total_bytes * 8) / (stats.duration_seconds * 1024)

        lines = [
            "# Informe de Diagnostico: AI Packet Doctor",
            (
                f"**Volumen Analizado:** {stats.total_packets} paquetes "
                f"({stats.total_bytes / 1024:.1f} KB) en {stats.duration_seconds:.2f}s"
            ),
            f"**Tasa de Trafico:** {pps:.1f} pkts/s | {kbps:.1f} Kbps",
            "",
            "## Distribucion de Protocolos",
        ]

        for proto, count in Counter(stats.protocol_counts).most_common(6):
            pct = (count / max(1, stats.total_packets)) * 100
            lines.append(f"- **{proto}:** {count} tramas ({pct:.1f}%)")

        lines.append("")
        lines.append("## Hallazgos y Diagnostico de Red")

        if not anomalies:
            lines.append("[ESTADO NORMAL] No se detectaron anomalias criticas ni caidas de flujo en la captura.")
        else:
            for idx, a in enumerate(anomalies, 1):
                badge = {
                    "CRITICAL": "[CRITICO]",
                    "HIGH": "[ALTO]",
                    "MEDIUM": "[MEDIO]",
                    "LOW": "[BAJO]",
                    "INFO": "[INFO]",
                }.get(a.severity, a.severity)

                lines.append(f"### {idx}. {badge} {a.title}")
                lines.append(f"**Categoria:** {a.category}")
                lines.append(f"**Descripcion:** {a.description}")
                if a.packet_indices:
                    pkts_str = ", ".join(f"#{i}" for i in a.packet_indices)
                    lines.append(f"**Tramas Clave de Evidencia:** {pkts_str}")
                lines.append(f"**Recomendacion de Remediacion:** {a.recommendation}")
                lines.append("")

        return "\n".join(lines)
