"""CLI command validation and injection prevention guardrail."""

import re
from typing import List

from networking_agent.core.exceptions import CommandInjectionError
from networking_agent.core.logging import logger

# Disallowed dangerous CLI keywords and injection vectors that must never be executed autonomously
FORBIDDEN_COMMAND_PATTERNS = [
    # System wipes, restarts, halts, and zeroization across Cisco, Juniper, and MikroTik
    re.compile(r"\b(format|erase|rmdir|boot|reload|reboot|halt|zeroize)\b", re.IGNORECASE),
    re.compile(r"\b(delete\s+(?:flash|nvram|bootflash|disk|harddisk|system|all|running-config))\b", re.IGNORECASE),
    re.compile(r"\b(?:system\s+)?reset-configuration\b", re.IGNORECASE),
    re.compile(r"\b(?:system\s+)?default-configuration\b", re.IGNORECASE),
    re.compile(r"\b(request\s+system\s+(?:zeroize|reboot|halt))\b", re.IGNORECASE),

    # Backdoor user creation, credential tampering, and authentication manipulation
    re.compile(r"\b(username|password|secret|radius|tacacs)\b", re.IGNORECASE),
    re.compile(r"\b(?:user\s+(?:add|set|remove)|login\s+user)\b", re.IGNORECASE),

    # Remote payload download, proxies, network flooding, persistence and underlying shell access
    re.compile(
        r"\b(tool\s+(?:fetch|traffic-generator|romon|bandwidth-test)|tftp-server|guestshell|start\s+shell)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(ip\s+(?:socks|proxy))\b", re.IGNORECASE),
    re.compile(r"\b(system\s+(?:script|scheduler|package))\b", re.IGNORECASE),

    # Core routing and crypto destruction
    re.compile(r"\b(no\s+ip\s+routing|no\s+router)\b", re.IGNORECASE),
    re.compile(r"\b(crypto\s+key\s+zeroize)\b", re.IGNORECASE),

    # Command chaining, redirection, background execution, and shell escaping
    re.compile(r"[\r\n;`$><&|\\]", re.IGNORECASE),
]


class CommandValidator:
    """Validates candidate CLI commands to prevent command injection and destructive actions."""

    @classmethod
    def validate_command_list(cls, commands: List[str]) -> List[str]:
        """Scans every command in the candidate list.

        Raises CommandInjectionError if any forbidden pattern is detected.
        """
        if not commands:
            return []

        validated: List[str] = []
        for cmd in commands:
            cmd_clean = cmd.strip()
            if not cmd_clean:
                continue

            for pattern in FORBIDDEN_COMMAND_PATTERNS:
                if pattern.search(cmd_clean):
                    err_msg = (
                        f"Security Guardrail Violation: Command '{cmd_clean}' matches forbidden "
                        f"pattern '{pattern.pattern}'."
                    )
                    logger.critical(f"[bold red]{err_msg}[/bold red]")
                    raise CommandInjectionError(err_msg)

            validated.append(cmd_clean)

        return validated
