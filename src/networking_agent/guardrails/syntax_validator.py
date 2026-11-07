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
            re.compile(r"\b(format\s+flash:|erase\s+startup-config|write\s+erase)\b", re.IGNORECASE),
            "Comando destructivo de almacenamiento no permitido.",
        ),
        (
            re.compile(r"\b(request\s+system\s+zeroize|zeroize)\b", re.IGNORECASE),
            "Comando destructivo de borrado seguro (zeroize) bloqueado.",
        ),
        (
            re.compile(r"\b(/system\s+reset-configuration)\b", re.IGNORECASE),
            "Reset a valores de fábrica bloqueado en RouterOS.",
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
            if vendor_family == "juniper_junos":
                if "{" in line:
                    junos_brace_balance += line.count("{")
                if "}" in line:
                    junos_brace_balance -= line.count("}")
            elif vendor_family in ["cisco_ios", "cisco_nxos"]:
                # Check for unmatched double quotes
                if line.count('"') % 2 != 0:
                    warnings.append(f"Línea {line_no}: Comillas dobles impares o no cerradas -> '{line}'")
            elif vendor_family == "mikrotik_routeros":
                if not line.startswith("/") and not line.startswith(":"):
                    warnings.append(
                        f"Línea {line_no}: El comando no inicia con '/' o ':'. RouterOS podría rechazarlo -> '{line}'"
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

        is_valid = len(errors) == 0

        return SyntaxValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            line_count=len(clean_commands),
            clean_commands=clean_commands,
        )
