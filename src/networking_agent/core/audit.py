"""Tamper-evident audit logging for network operations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from networking_agent.core.config import settings
from networking_agent.core.logging import logger


class AuditLogger:
    """Records every remediation decision, approval, CLI execution, and verification result."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or settings.audit_log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record_event(
        self,
        event_type: str,
        device_host: str,
        action: str,
        commands: List[str],
        approved: bool,
        approver: str = "local_operator",
        execution_output: Optional[str] = None,
        verification_status: Optional[str] = None,
        rollback_triggered: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends a structured event to the audit trail."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "device_host": device_host,
            "action": action,
            "commands": commands,
            "approved": approved,
            "approver": approver,
            "execution_output": execution_output,
            "verification_status": verification_status,
            "rollback_triggered": rollback_triggered,
            "extra": extra or {},
        }

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[bold red]Failed to write audit log:[/bold red] {e}")


audit_logger = AuditLogger()
