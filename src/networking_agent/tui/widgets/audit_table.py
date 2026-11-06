"""Audit trail table viewer displaying closed-loop events and verification logs."""

import json
from pathlib import Path
from typing import Any, Dict, List

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, DataTable, Label, Static

from networking_agent.core.config import settings


class AuditTableWidget(Static):
    """DataTable visualizer for logs/audit.jsonl."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("HISTORIAL CRIPTOGRÁFICO DE AUDITORÍA Y REMEDIACIONES", id="lbl-audit-header")
            yield DataTable(id="audit-data-table", cursor_type="row", zebra_stripes=True)
            yield Button("🔄 Actualizar Registro de Auditoría", id="btn-refresh-audit", variant="default")

    def on_mount(self) -> None:
        table = self.query_one("#audit-data-table", DataTable)
        table.add_columns(
            "Timestamp",
            "Tipo de Evento",
            "Equipo",
            "Acción",
            "Aprobado",
            "Verificación",
            "Comandos",
        )
        self.reload_audit_data()

    def reload_audit_data(self) -> None:
        """Parse audit.jsonl and populate table rows."""
        table = self.query_one("#audit-data-table", DataTable)
        table.clear()

        audit_file = Path(settings.audit_log_path)
        if not audit_file.exists():
            return

        records: List[Dict[str, Any]] = []
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        try:
                            records.append(json.loads(stripped))
                        except Exception:
                            continue
        except Exception:
            return

        # Show newest events first
        for rec in reversed(records[-100:]):
            ts = (rec.get("timestamp") or "")[:19]
            etype = rec.get("event_type") or "UNKNOWN"
            host = rec.get("device_host") or ""
            action = rec.get("action") or ""
            approved = "SÍ" if rec.get("approved") else "NO"
            vstatus = rec.get("verification_status") or "N/A"
            raw_cmds = rec.get("commands") or []
            cmds = ", ".join(raw_cmds) or "Ninguno"
            if len(cmds) > 30:
                cmds = cmds[:27] + "..."

            # Color coding
            etype_styled = Text(etype)
            if "SUCCESS" in etype or "NO_OP" in etype:
                etype_styled.stylize("bold green")
            elif "REJECTED" in etype or "FAILED" in etype:
                etype_styled.stylize("bold red")
            elif "OPERATOR" in etype:
                etype_styled.stylize("bold yellow")

            appr_styled = Text(approved)
            appr_styled.stylize("green" if approved == "SÍ" else "red")

            verif_styled = Text(vstatus)
            if vstatus == "PASSED":
                verif_styled.stylize("bold green")
            elif vstatus == "FAILED":
                verif_styled.stylize("bold red")

            table.add_row(
                ts,
                etype_styled,
                host,
                action,
                appr_styled,
                verif_styled,
                cmds,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-audit":
            self.reload_audit_data()
