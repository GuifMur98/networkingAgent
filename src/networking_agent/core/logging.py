"""Secure structured logging with automatic secret masking and Rich formatting."""

import logging
import re

from rich.console import Console
from rich.logging import RichHandler

console = Console()

# Patterns to mask sensitive fields in logs and audit trails
CLI_SENSITIVE_PATTERNS = [
    # Explicit assignment or statements like: "Password configured: ...", "Secret set to ..."
    re.compile(
        r"((?:password|secret)\s+(?:configured:\s*|set\s+to\s+|is\s+))([^\s\r\n,;'\"]+)",
        re.IGNORECASE,
    ),
    re.compile(r"((?:password|secret)['\"]?\s*[:=]\s*['\"]?)([^'\"]+)(['\"]?)", re.IGNORECASE),
    # Cisco / generic commands
    re.compile(r"((?:enable\s+secret|secret)\s+(?:0|5|8|9)?\s*)([^\s\r\n,;]+)", re.IGNORECASE),
    re.compile(r"((?:password)\s+(?:0|7)?\s*)([^\s\r\n,;]+)", re.IGNORECASE),
    re.compile(r"(snmp-server\s+community\s+)([^\s\r\n]+)", re.IGNORECASE),
    re.compile(r"((?:set\s+snmp|/snmp)\S*\s+(?:read|write)-community=)([^\s\r\n]+)", re.IGNORECASE),
    re.compile(r"((?:pre-shared-key|preshared-key|key\s+7|key)\s+)([^\s\r\n]+)", re.IGNORECASE),
    re.compile(r"((?:radius-server|tacacs-server)\s+key\s+)([^\s\r\n]+)", re.IGNORECASE),
    re.compile(r"(plain-text-password\s+)(['\"]?[^'\"]+['\"]?)", re.IGNORECASE),
    re.compile(r"(password=)(['\"]?[^\s'\"]+['\"]?)", re.IGNORECASE),
    re.compile(r"(api_key['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(token['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([^\s\r\n]+)", re.IGNORECASE),
]


def mask_sensitive_data(text: str) -> str:
    """Sanitizes passwords, secrets, tokens, and SNMP communities from strings, commands, and outputs."""
    if not text:
        return text
    result = text
    for pattern in CLI_SENSITIVE_PATTERNS:
        result = pattern.sub(r"\g<1>********", result)
    return result


class SecretMaskingFilter(logging.Filter):
    """Filters out passwords, API keys, and sensitive tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_data(record.msg)
        return True


def setup_logger(name: str = "networking_agent", level: int = logging.INFO) -> logging.Logger:
    """Configures a secure, formatted logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(console=console, rich_tracebacks=True, markup=True)
        handler.addFilter(SecretMaskingFilter())
        formatter = logging.Formatter("%(message)s", datefmt="[%X]")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
