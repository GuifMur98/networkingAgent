"""Multi-vendor configuration syntax checker and destructive command guardrail."""

import re
from typing import List, Optional

from pydantic import BaseModel, Field

from networking_agent.guardrails.validator import CommandValidator


class SyntaxValidationReport(BaseModel):
    """Structured report returned by the static syntax validator."""

    is_valid: bool = Field(..., description="True if no blocking errors or destructive commands were found.")
    errors: List[str] = Field(default_factory=list, description="List of fatal syntax errors or security violations.")
    warnings: List[str] = Field(default_factory=list, description="Advisories or best-practice warnings.")
    line_count: int = Field(default=0, description="Total number of non-empty lines evaluated.")
    clean_commands: List[str] = Field(
        default_factory=list, description="Sanitized list of parsed commands ready for execution."
    )


class ConfigSyntaxValidator:
    """Pre-flight analyzer verifying CLI scripts and templates before network injection."""

    FORBIDDEN_PATTERNS = [
        (
            re.compile(r"\b(reload|reboot|system\s+reboot)\b", re.IGNORECASE),
            "Comando de reinicio de equipo no permitido.",
        ),
        (
            re.compile(
                r"\b(format\s+flash:|format\s+bootflash:|erase\s+startup-config|write\s+erase)\b",
                re.IGNORECASE,
            ),
            "Comando destructivo de almacenamiento no permitido.",
        ),
        (
            re.compile(r"\b(request\s+system\s+zeroize|zeroize)\b", re.IGNORECASE),
            "Comando destructivo de borrado seguro (zeroize) bloqueado.",
        ),
        (
            re.compile(r"\b(/system\s+reset-configuration|/system/reset-configuration)\b", re.IGNORECASE),
            "Reset a valores de fábrica bloqueado en RouterOS.",
        ),
        (
            re.compile(r"\b(/disk\s+format|/system\s+backup\s+load)\b", re.IGNORECASE),
            "Comando destructivo de almacenamiento/backup bloqueado en RouterOS.",
        ),
        (
            re.compile(r"[;&|`]", re.IGNORECASE),
            "Metacarácter de encadenamiento de comandos detectado.",
        ),
        (
            re.compile(r"\b(rm\s+-rf|nc\s+-e|/bin/sh|/bin/bash)\b", re.IGNORECASE),
            "Comando de ejecución de shell no permitido.",
        ),
    ]

    UNRENDERED_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")

    # Regex patterns for vendor-specific syntactic validation
    CISCO_INTERFACE_CIDR_PATTERN = re.compile(r"^ip\s+address\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}", re.I)
    CISCO_OSPF_NET_SUBNET_PATTERN = re.compile(
        r"^network\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+255\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+area",
        re.I,
    )
    CISCO_VLAN_RANGE_PATTERN = re.compile(r"^vlan\s+(\d+)\b", re.I)
    JUNOS_DECIMAL_MASK_PATTERN = re.compile(
        r"\baddress\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+255\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        re.I,
    )
    ROUTEROS_SPACED_EQUAL_PATTERN = re.compile(r"\b([a-zA-Z0-9_\-]+)\s+=\s*|\b([a-zA-Z0-9_\-]+)\s*=\s+")
    ROUTEROS_V6_OSPF_NET = re.compile(r"^/routing\s+ospf\s+network\b", re.I)
    ROUTEROS_V6_BGP_PEER = re.compile(r"^/routing\s+bgp\s+peer\b", re.I)

    @classmethod
    def validate_script(
        cls,
        raw_text: str,
        vendor_family: Optional[str] = "cisco_ios",
    ) -> SyntaxValidationReport:
        """Analyzes a script or configuration block for syntax integrity and safety.

        Args:
            raw_text: The multi-line text pasted or loaded by the operator.
            vendor_family: Target OS family (cisco_ios, cisco_nxos, juniper_junos, mikrotik_routeros).

        Returns:
            SyntaxValidationReport with validation status, line-by-line errors, and sanitized command list.
        """
        errors: List[str] = []
        warnings: List[str] = []
        clean_commands: List[str] = []

        if not raw_text or not raw_text.strip():
            return SyntaxValidationReport(
                is_valid=False,
                errors=["El script está vacío. Pegue o escriba comandos de configuración."],
                warnings=[],
                line_count=0,
                clean_commands=[],
            )

        lines = raw_text.splitlines()
        junos_brace_balance = 0

        # NX-OS feature tracking
        nxos_has_ospf_cmd = False
        nxos_has_ospf_feature = False
        nxos_has_bgp_cmd = False
        nxos_has_bgp_feature = False
        nxos_has_svi_cmd = False
        nxos_has_svi_feature = False

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            # Ignore empty lines and comments
            if not line or line.startswith("!") or line.startswith("#"):
                continue

            # 1. Check for unrendered template variables
            unrendered = cls.UNRENDERED_VARIABLE_PATTERN.findall(line)
            if unrendered:
                errors.append(
                    f"Línea {line_no}: Variable de plantilla sin renderizar detectada: {', '.join(unrendered)}"
                )

            # 2. Check for destructive and forbidden patterns
            for pattern, reason in cls.FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    errors.append(f"Línea {line_no}: [SEGURIDAD] {reason} -> '{line}'")

            # 3. Vendor-specific syntax checks
            if vendor_family in ["cisco_ios", "cisco_nxos"]:
                if line.count('"') % 2 != 0:
                    warnings.append(f"Línea {line_no}: Comillas dobles impares o no cerradas -> '{line}'")

                # Detect wrong OS commands pasted
                if line.startswith("set ") or line.startswith("/"):
                    errors.append(
                        f"Línea {line_no}: Sintaxis incompatible con {vendor_family}. "
                        f"Detectado comando de Junos o RouterOS -> '{line}'"
                    )

                if vendor_family == "cisco_ios":
                    # Check CIDR vs dotted decimal on interface
                    if cls.CISCO_INTERFACE_CIDR_PATTERN.search(line):
                        warnings.append(
                            f"Línea {line_no}: Cisco IOS requiere máscara decimal separada por espacios "
                            f"(ej: 192.168.1.1 255.255.255.0) en vez de CIDR -> '{line}'"
                        )

                    # Check OSPF network wildcard vs normal subnet mask
                    if cls.CISCO_OSPF_NET_SUBNET_PATTERN.search(line):
                        warnings.append(
                            f"Línea {line_no}: OSPF en Cisco IOS requiere máscara wildcard invertida "
                            f"(ej: 0.0.0.255) en lugar de máscara decimal de subred (255.255.255.0) -> '{line}'"
                        )

                    # Check VLAN range
                    vlan_match = cls.CISCO_VLAN_RANGE_PATTERN.match(line)
                    if vlan_match:
                        vlan_id = int(vlan_match.group(1))
                        if vlan_id < 1 or vlan_id > 4094:
                            errors.append(f"Línea {line_no}: ID de VLAN {vlan_id} inválido (rango permitido: 1-4094).")

                elif vendor_family == "cisco_nxos":
                    # Track feature activation
                    if line.lower() == "feature ospf":
                        nxos_has_ospf_feature = True
                    elif line.lower() == "feature bgp":
                        nxos_has_bgp_feature = True
                    elif line.lower() == "feature interface-vlan":
                        nxos_has_svi_feature = True
                    elif line.lower().startswith("router ospf"):
                        nxos_has_ospf_cmd = True
                    elif line.lower().startswith("router bgp"):
                        nxos_has_bgp_cmd = True
                    elif line.lower().startswith("interface vlan"):
                        nxos_has_svi_cmd = True

            elif vendor_family == "juniper_junos":
                if "{" in line:
                    junos_brace_balance += line.count("{")
                if "}" in line:
                    junos_brace_balance -= line.count("}")

                # Reject Cisco syntax in Junos
                if line.startswith("interface ") or line.startswith("router ospf") or line.startswith("no shutdown"):
                    errors.append(
                        f"Línea {line_no}: Sintaxis de Cisco detectada en Junos. "
                        f"En Junos utilice 'set interfaces ...' o bloques jerárquicos -> '{line}'"
                    )

                # Junos requires CIDR prefix notation, never dotted decimal
                if cls.JUNOS_DECIMAL_MASK_PATTERN.search(line):
                    errors.append(
                        f"Línea {line_no}: Junos no admite máscaras de red decimales (255.x.x.x). "
                        f"Utilice notación CIDR obligatoria (ej: 192.168.1.1/24) -> '{line}'"
                    )

            elif vendor_family == "mikrotik_routeros":
                if not line.startswith("/") and not line.startswith(":"):
                    errors.append(f"Línea {line_no}: El comando RouterOS debe iniciar con '/' o ':' -> '{line}'")

                # Check spaces around equals in key=value arguments
                if "=" in line:
                    for part in line.split():
                        if part == "=":
                            warnings.append(
                                f"Línea {line_no}: Espacios detectados alrededor del operador '='. "
                                f"En RouterOS los parámetros deben ser compactos (ej: address=10.0.0.1/24) -> '{line}'"
                            )
                            break

                # Detect RouterOS v6 vs v7 routing differences
                if cls.ROUTEROS_V6_OSPF_NET.search(line):
                    warnings.append(
                        f"Línea {line_no}: [RouterOS v6->v7] '/routing ospf network' es obsoleto en v7. "
                        f"En v7 use '/routing ospf instance add' y '/routing ospf area add'."
                    )
                if cls.ROUTEROS_V6_BGP_PEER.search(line):
                    warnings.append(
                        f"Línea {line_no}: [RouterOS v6->v7] '/routing bgp peer' es obsoleto en v7. "
                        f"En v7 use '/routing bgp connection add'."
                    )

            # 4. Command Validator check
            try:
                CommandValidator.validate(line)
                clean_commands.append(line)
            except Exception as e:
                errors.append(f"Línea {line_no}: [GUARDARRAÍL] {e}")

        # Check Juniper brace matching
        if vendor_family == "juniper_junos" and junos_brace_balance != 0:
            errors.append(
                f"Sintaxis Junos inválida: Bloques jerárquicos desbalanceados (balance: {junos_brace_balance})"
            )

        # Check NX-OS missing features
        if vendor_family == "cisco_nxos":
            if nxos_has_ospf_cmd and not nxos_has_ospf_feature:
                warnings.append("Cisco NX-OS: Se detectó 'router ospf' sin declarar previamente 'feature ospf'.")
            if nxos_has_bgp_cmd and not nxos_has_bgp_feature:
                warnings.append("Cisco NX-OS: Se detectó 'router bgp' sin declarar previamente 'feature bgp'.")
            if nxos_has_svi_cmd and not nxos_has_svi_feature:
                warnings.append(
                    "Cisco NX-OS: Se detectó 'interface Vlan' sin declarar previamente 'feature interface-vlan'."
                )

        is_valid = len(errors) == 0

        return SyntaxValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            line_count=len(clean_commands),
            clean_commands=clean_commands,
        )
