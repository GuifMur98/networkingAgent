"""Secure structured logging with automatic secret masking and Rich formatting."""

import logging
import re

from rich.console import Console
from rich.logging import RichHandler

console = Console()

# Patterns to mask sensitive fields in logs
SENSITIVE_PATTERNS = [
    re.compile(r"(password['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(secret['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(api_key['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(token['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
]


class SecretMaskingFilter(logging.Filter):
    """Filters out passwords, API keys, and sensitive tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(r"\1********\3", record.msg)
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
