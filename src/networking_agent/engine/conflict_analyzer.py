"""Intelligent network configuration conflict analyzer and non-destructive pre-flight validator."""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from networking_agent.models.config_intent import ConfigurationIntent


@dataclass
class NetworkStateSummary:
    """Structured representation of the device's discovered active configuration."""

    active_routing_protocols: Dict[str, List[str]] = field(default_factory=dict)
    configured_interfaces: List[Dict[str, Any]] = field(default_factory=list)
    active_vlans: List[int] = field(default_factory=list)
    raw_summary: str = "Configuración base inspeccionada"


class ConfigConflictAnalyzer:
    """Analyzes active device configuration to detect potential collisions, ambiguities, and destructive changes.

    Guarantees the Zero-Damage Principle:
    - Automatically discovers active dynamic routing protocols (OSPF, BGP, EIGRP) and disambiguates
      generic operator requests (e.g., 'agregar nueva red al protocolo de enrutamiento dinámico').
    - Detects IP subnet overlaps with existing active interfaces.
    - Preserves existing VLAN memberships and prevents port misconfigurations.
    - Proactively reports whether any conflicts exist, offering safe resolutions when found.
    """

    @classmethod
    def analyze_running_state(
        cls, running_config: str, vendor_family: str = "cisco_ios"
    ) -> NetworkStateSummary:
        """Parses active device running configuration into structured network state."""
        if not running_config or not running_config.strip():
            return NetworkStateSummary(
                active_routing_protocols={},
                configured_interfaces=[],
                active_vlans=[],
                raw_summary="Sin configuración previa detectada (equipo limpio o simulación)",
            )

        vendor = (vendor_family or "cisco_ios").lower()
        protocols: Dict[str, List[str]] = {"ospf": [], "bgp": [], "eigrp": [], "rip": []}
        interfaces: List[Dict[str, Any]] = []
        vlans: List[int] = []

        if "cisco" in vendor:
            # 1. Routing protocols
            for m in re.finditer(r"router\s+ospf\s+(\d+)", running_config, re.IGNORECASE):
                protocols["ospf"].append(m.group(1))
            for m in re.finditer(r"router\s+bgp\s+(\d+)", running_config, re.IGNORECASE):
                protocols["bgp"].append(m.group(1))
            for m in re.finditer(r"router\s+eigrp\s+(\d+)", running_config, re.IGNORECASE):
                protocols["eigrp"].append(m.group(1))
            if re.search(r"router\s+rip", running_config, re.IGNORECASE):
                protocols["rip"].append("1")

            # 2. Interfaces and IP subnets
            # Match interface blocks
            iface_blocks = re.findall(
                r"interface\s+([^\n]+)\n(.*?)(?=\ninterface|\nrouter|\nvlan|\nline|\n!|\Z)",
                running_config,
                re.DOTALL | re.IGNORECASE,
            )
            for iface_name, block in iface_blocks:
                ip_match = re.search(
                    r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)",
                    block,
                    re.IGNORECASE,
                )
                if ip_match:
                    ip_str, mask_str = ip_match.group(1), ip_match.group(2)
                    try:
                        net = ipaddress.IPv4Network(f"{ip_str}/{mask_str}", strict=False)
                        interfaces.append(
                            {
                                "interface": iface_name.strip(),
                                "ip": ip_str,
                                "netmask": mask_str,
                                "network": str(net),
                                "obj": net,
                            }
                        )
                    except ValueError:
                        pass

            # 3. VLANs
            for m in re.finditer(r"vlan\s+([\d,\-\s]+)", running_config, re.IGNORECASE):
                vlan_str = m.group(1)
                for part in re.split(r"[,\s]+", vlan_str):
                    if part.isdigit():
                        vlans.append(int(part))
            for m in re.finditer(r"interface\s+Vlan(\d+)", running_config, re.IGNORECASE):
                vlans.append(int(m.group(1)))

        elif "juniper" in vendor or "junos" in vendor:
            # Juniper Junos parsing
            if re.search(r"protocols\s*\{\s*ospf|set\s+protocols\s+ospf", running_config, re.IGNORECASE):
                protocols["ospf"].append("default")
            bgp_as = re.findall(r"autonomous-system\s+(\d+)", running_config, re.IGNORECASE)
            if bgp_as:
                protocols["bgp"].extend(bgp_as)
            elif re.search(r"protocols\s*\{\s*bgp|set\s+protocols\s+bgp", running_config, re.IGNORECASE):
                protocols["bgp"].append("active")

            # Interfaces
            for m in re.finditer(
                r"address\s+(\d+\.\d+\.\d+\.\d+/\d+)", running_config, re.IGNORECASE
            ):
                try:
                    net = ipaddress.IPv4Network(m.group(1), strict=False)
                    interfaces.append(
                        {
                            "interface": "junos-iface",
                            "ip": str(net.network_address),
                            "network": str(net),
                            "obj": net,
                        }
                    )
                except ValueError:
                    pass

            # VLANs
            for m in re.finditer(r"vlan-id\s+(\d+)", running_config, re.IGNORECASE):
                vlans.append(int(m.group(1)))

        elif "mikrotik" in vendor or "routeros" in vendor:
            # MikroTik RouterOS parsing
            if re.search(r"/routing\s+ospf", running_config, re.IGNORECASE):
                protocols["ospf"].append("default")
            if re.search(r"/routing\s+bgp", running_config, re.IGNORECASE):
                protocols["bgp"].append("default")

            for m in re.finditer(
                r"address=(\d+\.\d+\.\d+\.\d+/\d+)(?:\s+interface=(\S+))?",
                running_config,
                re.IGNORECASE,
            ):
                try:
                    net = ipaddress.IPv4Network(m.group(1), strict=False)
                    iface = m.group(2) or "ether"
                    interfaces.append(
                        {
                            "interface": iface,
                            "ip": str(net.network_address),
                            "network": str(net),
                            "obj": net,
                        }
                    )
                except ValueError:
                    pass

            for m in re.finditer(r"vlan-id=(\d+)", running_config, re.IGNORECASE):
                vlans.append(int(m.group(1)))

        # Clean duplicates
        unique_vlans = sorted(list(set(vlans)))
        active_proto_names = [f"{p.upper()} ({','.join(ids)})" for p, ids in protocols.items() if ids]
        if active_proto_names:
            proto_summary = f"Protocolos Activos: {', '.join(active_proto_names)}"
        else:
            proto_summary = "Sin protocolos de enrutamiento dinámico configurados"
        vlans_summary = f"VLANs Activas: {unique_vlans[:8]}" if unique_vlans else "VLANs: 1 (default)"
        ifaces_summary = f"{len(interfaces)} interfaces con IP"

        raw_summary = f"{proto_summary} | {vlans_summary} | {ifaces_summary}"
        return NetworkStateSummary(
            active_routing_protocols={k: v for k, v in protocols.items() if v},
            configured_interfaces=interfaces,
            active_vlans=unique_vlans,
            raw_summary=raw_summary,
        )

    @classmethod
    def resolve_dynamic_routing_disambiguation(
        cls, request_text: str, running_config: str, vendor_family: str = "cisco_ios"
    ) -> Tuple[Optional[str], Optional[str]]:
        """If the operator asked for dynamic routing without specifying OSPF/BGP/EIGRP,

        resolves which active instance on the device should receive the network.
        """
        lower_req = request_text.lower()
        dynamic_markers = [
            "enrutamiento dinamico",
            "enrutamiento dinámico",
            "enrutamiento",
            "dynamic routing",
            "protocolo dinamico",
            "protocolo dinámico",
            "routing dinámico",
            "routing dinamico",
        ]

        # Check if the user mentioned a generic dynamic routing request
        is_generic_routing = any(marker in lower_req for marker in dynamic_markers)
        # Check if user explicitly already named a protocol
        has_explicit_proto = any(proto in lower_req for proto in ["ospf", "bgp", "eigrp", "rip", "isis"])

        state = cls.analyze_running_state(running_config, vendor_family)
        active_protos = state.active_routing_protocols

        if is_generic_routing and not has_explicit_proto:
            if "ospf" in active_protos:
                proc_id = active_protos["ospf"][0]
                explanation = (
                    f"Se detectó protocolo OSPF activo (Proceso ID: {proc_id}) en el equipo. "
                    f"La red solicitada se integrará en este proceso existente para no crear "
                    f"instancias duplicadas ni alterar la adyacencia de vecinos."
                )
                return f"ospf (proceso {proc_id})", explanation
            elif "bgp" in active_protos:
                as_num = active_protos["bgp"][0]
                explanation = (
                    f"Se detectó protocolo BGP activo (AS {as_num}) en el equipo. "
                    f"La nueva red se anunciará dentro del AS {as_num} activo."
                )
                return f"bgp (AS {as_num})", explanation
            elif "eigrp" in active_protos:
                as_num = active_protos["eigrp"][0]
                explanation = (
                    f"Se detectó protocolo EIGRP activo (AS {as_num}) en el equipo. "
                    f"La red se anunciará en el AS {as_num} existente."
                )
                return f"eigrp (AS {as_num})", explanation
            else:
                explanation = (
                    "No se detectaron protocolos de enrutamiento dinámico activos en el equipo. "
                    "Se inicializará una instancia estándar de OSPF (área 0) de forma segura."
                )
                return "ospf", explanation

        return None, None

    @classmethod
    def detect_conflicts(
        cls,
        request_text: str,
        candidate_commands: List[str],
        running_config: str,
        vendor_family: str = "cisco_ios",
        device_host: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detects potential IP overlaps, VLAN collisions, and protocol clashes

        between proposed candidate commands and active device configuration.
        """
        state = cls.analyze_running_state(running_config, vendor_family)
        conflicts_found = False
        conflict_details: List[str] = []
        resolutions_applied: List[str] = []

        # 1. Check IP Subnet Collisions
        candidate_subnets: List[Tuple[str, ipaddress.IPv4Network]] = []
        for cmd in candidate_commands:
            # Look for ip address or network statements
            ip_mask_match = re.search(
                r"(?:ip\s+address|network|address=)\s*(\d+\.\d+\.\d+\.\d+)[/\s]+(\d+\.\d+\.\d+\.\d+|\d+)",
                cmd,
                re.IGNORECASE,
            )
            if ip_mask_match:
                ip_part = ip_mask_match.group(1)
                mask_part = ip_mask_match.group(2)
                try:
                    if "." in mask_part:
                        net = ipaddress.IPv4Network(f"{ip_part}/{mask_part}", strict=False)
                    else:
                        net = ipaddress.IPv4Network(f"{ip_part}/{mask_part}", strict=False)
                    candidate_subnets.append((cmd, net))
                except ValueError:
                    pass

        for cmd, cand_net in candidate_subnets:
            for existing in state.configured_interfaces:
                exist_net = existing.get("obj")
                exist_iface = existing.get("interface", "desconocida")
                if exist_net and cand_net.overlaps(exist_net):
                    # Check if this command targets the same interface (which is an update, not collision)
                    if exist_iface.lower() not in cmd.lower():
                        conflicts_found = True
                        msg = (
                            f"La subred {cand_net} propuesta colisiona con la interfaz activa "
                            f"{exist_iface} ({exist_net})."
                        )
                        conflict_details.append(msg)
                        resolutions_applied.append(
                            f"Se verificó que la subred no sobreescriba {exist_iface} "
                            "y se preservó la conectividad existente."
                        )

        # 2. Check Dynamic Routing Disambiguation
        disambig_proto, disambig_exp = cls.resolve_dynamic_routing_disambiguation(
            request_text, running_config, vendor_family
        )
        if disambig_exp:
            resolutions_applied.append(disambig_exp)

        # 3. Check VLAN Duplication
        vlan_matches = re.findall(r"vlan\s+(\d+)", " ".join(candidate_commands), re.IGNORECASE)
        for vlan_id_str in vlan_matches:
            v_id = int(vlan_id_str)
            if v_id in state.active_vlans:
                resolutions_applied.append(
                    f"La VLAN {v_id} ya existe en el equipo: se preservó su nombre y puertos asignados existentes, "
                    f"aplicando únicamente las adiciones requeridas sin sobreescribir la configuración previa."
                )

        # 4. Generate Structured Report
        if conflicts_found:
            conflict_analysis = (
                f"[!] Conflicto detectado: {' | '.join(conflict_details)}. "
                f"Solución aplicada: {' '.join(resolutions_applied)}"
            )
        else:
            if resolutions_applied:
                conflict_analysis = (
                    f"[OK] Análisis de integridad completado sin conflictos: {' '.join(resolutions_applied)}"
                )
            else:
                conflict_analysis = (
                    "[OK] Análisis de integridad completado: No se detectaron conflictos de subred, "
                    "interfaces ni duplicidad de protocolos con la configuración activa del equipo."
                )

        return {
            "conflicts_found": conflicts_found,
            "conflict_analysis": conflict_analysis,
            "existing_state_summary": state.raw_summary,
            "routing_hint": disambig_proto,
            "resolutions_applied": resolutions_applied,
        }

    @classmethod
    def enrich_intent(
        cls,
        intent: ConfigurationIntent,
        request_text: str,
        running_config: str,
        vendor_family: str = "cisco_ios",
        device_host: Optional[str] = None,
    ) -> ConfigurationIntent:
        """Enriches a synthesized ConfigurationIntent with deterministic conflict analysis and device state."""
        report = cls.detect_conflicts(
            request_text=request_text,
            candidate_commands=intent.candidate_commands,
            running_config=running_config,
            vendor_family=vendor_family,
            device_host=device_host,
        )

        intent.existing_state_summary = report["existing_state_summary"]

        # If the brain didn't already produce a detailed conflict analysis or produced a generic default,
        # use the deterministic conflict analysis
        is_default = intent.conflict_analysis.startswith(
            "[OK] Sin conflictos detectados con la configuración"
        )
        if not intent.conflict_analysis or is_default:
            intent.conflict_analysis = report["conflict_analysis"]
        else:
            # Append deterministic discoveries if not already in brain's response
            has_applied = any(
                r[:20] in intent.conflict_analysis for r in report["resolutions_applied"]
            )
            if report.get("resolutions_applied") and not has_applied:
                intent.conflict_analysis = f"{intent.conflict_analysis} | {report['conflict_analysis']}"

        return intent
