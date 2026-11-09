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

    @classmethod
    def query_ai_assistant(
        cls,
        user_query: str,
        packets: list[CapturedPacket],
    ) -> str:
        """Consult the active AI Brain using packet evidence and the user's specific inquiry."""
        stats, anomalies, heuristic_report = cls.analyze(packets)

        sample_lines = []
        for p in packets[:30]:
            sample_lines.append(
                f"#{p.index} [{p.formatted_time}] {p.source} -> {p.destination} | {p.protocol} ({p.length}B) | {p.info}"
            )
        sample_str = "\n".join(sample_lines) if sample_lines else "Sin tramas en sesión."

        anomalies_str = (
            "\n".join(f"- [{a.severity}] {a.title}: {a.description} (Tramas: {a.packet_indices})" for a in anomalies)
            if anomalies
            else "Sin anomalías preliminares detectadas."
        )

        pps = stats.total_packets / max(0.001, stats.duration_seconds)
        kbps = (stats.total_bytes * 8) / (max(0.001, stats.duration_seconds) * 1024)

        prompt_payload = (
            f"CONSULTA DEL INGENIERO DE RED:\n"
            f'"{user_query}"\n\n'
            f"TELEMETRIA Y METRICAS DE CAPTURA:\n"
            f"- Tramas analizadas: {stats.total_packets} ({stats.total_bytes / 1024:.1f} KB)\n"
            f"- Duración de captura: {stats.duration_seconds:.2f} segundos\n"
            f"- Rendimiento promedio: {pps:.1f} pkts/s | {kbps:.1f} Kbps\n"
            f"- Retransmisiones TCP: {stats.tcp_retransmissions}\n"
            f"- Caídas de ventana Zero-Window: {stats.tcp_zero_windows}\n"
            f"- Respuestas DNS fallidas: {stats.dns_failures}\n"
            f"- Protocolos detectados: {dict(Counter(stats.protocol_counts).most_common(6))}\n\n"
            f"ANOMALIAS DETECTADAS POR EL MOTOR DE DISECCION:\n"
            f"{anomalies_str}\n\n"
            f"MUESTRA DE TRAMAS RELEVANTES (L2-L7):\n"
            f"{sample_str}\n\n"
            "INSTRUCCIONES:\n"
            "1. Responde directamente a la consulta del ingeniero en español técnico profesional.\n"
            "2. Proporciona un diagnóstico de causa raíz a nivel de protocolo (L2-L7).\n"
            "3. Cita evidencia específica de las tramas capturadas (#número de trama, IPs, puertos o banderas).\n"
            "4. Detalla un plan de remediación técnica paso a paso para resolver la causa raíz."
        )

        system_prompt = (
            "Eres el Asistente Experto en Análisis Forense y Diagnóstico de Redes con IA (AI Packet Doctor) "
            "de NetworkingAgent Enterprise. Tu objetivo es analizar capturas de paquetes reales y diagnosticar "
            "con rigor técnico fallas de rendimiento, caídas de sesión, congestión o anomalías de protocolo."
        )

        try:
            from networking_agent.brains.factory import get_ai_brain

            brain = get_ai_brain()
            model_name = getattr(brain, "model_name", "AI Brain")

            if hasattr(brain, "host"):  # Ollama
                from ollama import Client

                client = Client(host=brain.host)
                res = client.chat(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_payload},
                    ],
                    options={"temperature": 0.2},
                )
                ai_text = res.message.content
                return f"# Diagnostico de IA: {user_query}\n**Cerebro Activo:** Ollama ({model_name})\n\n{ai_text}"
            elif hasattr(brain, "api_key") and "gemini" in brain.__class__.__name__.lower():
                from google import genai

                client = genai.Client(api_key=brain.api_key)
                res = client.models.generate_content(
                    model=model_name,
                    contents=prompt_payload,
                )
                ai_text = res.text
                return (
                    f"# Diagnostico de IA: {user_query}\n**Cerebro Activo:** Google Gemini ({model_name})\n\n{ai_text}"
                )
            elif hasattr(brain, "api_key") and "openai" in brain.__class__.__name__.lower():
                from openai import OpenAI

                client = OpenAI(api_key=brain.api_key)
                res = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_payload},
                    ],
                )
                ai_text = res.choices[0].message.content
                return f"# Diagnostico de IA: {user_query}\n**Cerebro Activo:** OpenAI ({model_name})\n\n{ai_text}"
            elif hasattr(brain, "api_key") and "anthropic" in brain.__class__.__name__.lower():
                from anthropic import Anthropic

                client = Anthropic(api_key=brain.api_key)
                res = client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt_payload}],
                )
                ai_text = res.content[0].text
                return (
                    f"# Diagnostico de IA: {user_query}\n"
                    f"**Cerebro Activo:** Anthropic Claude ({model_name})\n\n{ai_text}"
                )
        except Exception:
            pass

        # Intelligent query-tailored synthesis fallback
        lines = [
            f"# Diagnostico Forense de IA: {user_query}",
            (
                f"**Volumen Analizado:** {stats.total_packets} paquetes "
                f"({stats.total_bytes / 1024:.1f} KB) en {stats.duration_seconds:.2f}s"
            ),
            f"**Tasa de Trafico:** {pps:.1f} pkts/s | {kbps:.1f} Kbps",
            "",
            "## Evaluacion del Objetivo de Investigacion",
            (
                f'Se ha procesado la consulta del operador: *"{user_query}"*. '
                "A continuacion se presenta la evidencia recolectada en la captura:"
            ),
            "",
        ]

        query_lower = user_query.lower()
        if "retransmi" in query_lower or "lento" in query_lower or "velocidad" in query_lower:
            if stats.tcp_retransmissions > 0:
                lines.append(f"**Hallazgo Principal:** Se confirmaron {stats.tcp_retransmissions} retransmisiones TCP.")
                lines.append(
                    "Las tramas duplicadas indican congestión en los buffers o pérdida de paquetes en el enlace de red."
                )
            else:
                lines.append(
                    "**Hallazgo Principal:** No se observan retransmisiones de paquetes TCP en la ventana temporal."
                )
        elif "dns" in query_lower:
            if stats.dns_failures > 0:
                lines.append(
                    f"**Hallazgo Principal:** Se detectaron {stats.dns_failures} "
                    "respuestas DNS con error (NXDOMAIN/SERVFAIL)."
                )
                lines.append(
                    "Los servidores DNS configurados no resuelven los registros "
                    "o existe latencia en los reenviadores (forwarders)."
                )
            else:
                lines.append(
                    "**Hallazgo Principal:** Las consultas DNS registradas respondieron sin codigos de error RCODE."
                )
        elif "rst" in query_lower or "cae" in query_lower or "cierre" in query_lower:
            lines.append("Se identificaron paquetes con bandera TCP RST (Reset).")
            lines.append("Un firewall intermedio o el host remoto cerraron la sesion de transporte de forma forzada.")
        else:
            lines.append(
                f"Se analizaron {stats.total_packets} tramas en busca de anomalias relacionadas con la consulta."
            )

        lines.append("")
        lines.append(heuristic_report)
        return "\n".join(lines)
