"""CLI command validation and injection prevention guardrail."""

import re
from typing import List

from networking_agent.core.exceptions import CommandInjectionError
from networking_agent.core.logging import logger

# Disallowed dangerous CLI keywords that should never be executed autonomously
FORBIDDEN_COMMAND_PATTERNS = [
    re.compile(r"\b(format|erase|delete|rmdir|boot|reload)\b", re.IGNORECASE),
    re.compile(r"\b(username|password|secret|radius|tacacs)\b", re.IGNORECASE),
    re.compile(r"\b(no\s+ip\s+routing|no\s+router)\b", re.IGNORECASE),
    re.compile(r"\b(crypto\s+key\s+zeroize)\b", re.IGNORECASE),
    re.compile(r"[\r\n;`$><]", re.IGNORECASE),  # Newlines, semicolons, shell pipes/redirections
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
