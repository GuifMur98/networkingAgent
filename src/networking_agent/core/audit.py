"""Tamper-evident audit logging with cryptographic SHA-256 hash chaining and credential sanitization."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from networking_agent.core.config import settings
from networking_agent.core.logging import logger, mask_sensitive_data

GENESIS_HASH = "GENESIS_0000000000000000000000000000000000000000000000000000000000000000"


class AuditLogger:
    """Records every remediation decision, approval, CLI execution, and verification result with SHA-256 chaining."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or settings.audit_log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_last_hash(self) -> str:
        """Retrieves the cryptographic event_hash from the last recorded line in audit.jsonl."""
        if not self.log_path.exists():
            return GENESIS_HASH
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines:
                return GENESIS_HASH
            last_record = json.loads(lines[-1])
            return str(last_record.get("event_hash", GENESIS_HASH))
        except Exception:
            return GENESIS_HASH

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
        """Appends a structured, sanitized, and cryptographically chained event to the audit trail."""
        # 1. Sanitize sensitive credentials from commands and execution outputs (VULN-06)
        sanitized_commands = [mask_sensitive_data(cmd) for cmd in commands]
        sanitized_output = mask_sensitive_data(execution_output) if execution_output else None

        # 2. Cryptographic SHA-256 chaining (VULN-07)
        prev_hash = self._get_last_hash()

        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "device_host": device_host,
            "action": action,
            "commands": sanitized_commands,
            "approved": approved,
            "approver": approver,
            "execution_output": sanitized_output,
            "verification_status": verification_status,
            "rollback_triggered": rollback_triggered,
            "extra": extra or {},
            "prev_hash": prev_hash,
        }

        # Calculate canonical SHA-256 hash of event contents
        canonical_payload = json.dumps(record, sort_keys=True, ensure_ascii=False)
        record["event_hash"] = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[bold red]Failed to write audit log:[/bold red] {e}")


def verify_audit_integrity(log_path: Optional[Path] = None) -> Tuple[bool, int, Optional[str]]:
    """Cryptographically verifies the SHA-256 hash chaining of an audit log file.

    Returns:
        (is_valid, record_count, error_message)
    """
    target_path = log_path or settings.audit_log_path
    if not target_path.exists():
        return True, 0, None

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        return False, 0, f"Failed to read audit log: {e}"

    if not lines:
        return True, 0, None

    expected_prev = GENESIS_HASH
    for idx, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except Exception as e:
            return False, idx, f"Line {idx}: Corrupt JSON syntax ({e})"

        recorded_hash = record.get("event_hash")
        prev_hash = record.get("prev_hash")

        # Backward compatibility: records before v2.1.1 without hash chaining
        if not recorded_hash or not prev_hash:
            continue

        if prev_hash != expected_prev:
            return False, idx, f"Line {idx}: prev_hash '{prev_hash}' does not match expected '{expected_prev}'"

        # Recompute hash
        unhashed_copy = dict(record)
        unhashed_copy.pop("event_hash", None)
        canonical = json.dumps(unhashed_copy, sort_keys=True, ensure_ascii=False)
        calculated_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        if calculated_hash != recorded_hash:
            return (
                False,
                idx,
                f"Line {idx}: Hash mismatch! Calculated '{calculated_hash}' vs recorded '{recorded_hash}'",
            )

        expected_prev = recorded_hash

    return True, len(lines), None


audit_logger = AuditLogger()
