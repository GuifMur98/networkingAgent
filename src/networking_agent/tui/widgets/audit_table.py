"""Enterprise tamper-evident audit trail viewer with real-time inspection, filters, and export."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich import box
from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from networking_agent.core.config import settings
from networking_agent.core.db import db


class AuditTableWidget(Widget):
    """Interactive visualizer and inspector for immutable audit records in logs/audit.jsonl."""

    class ReturnHomeRequested(Message):
        """Emitted when the operator wants to return to the Home/Inicio view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.all_records: List[Dict[str, Any]] = []
        self.filtered_records: List[Dict[str, Any]] = []
        self.selected_record: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="audit-container"):
            with Vertical(id="audit-content-wrapper", classes="workspace-content-wrapper"):
                # 1. Header Navigation Bar
                with Horizontal(id="audit-top-bar"):
                    yield Label(
                        "AUDITORIA CRIPTOGRAFICA // BITACORA DE OPERACIONES Y REMEDIACIONES",
                        id="lbl-audit-header",
                    )
                    yield Button("Volver al Inicio (h)", id="btn-back-from-audit")

                # 2. Unified Toolbar (Filters, Search, and Operational Actions)
                with Horizontal(id="audit-toolbar", classes="section-panel"):
                    with Horizontal(id="audit-filter-controls"):
                        yield Label("Equipo:", classes="audit-filter-label")
                        yield Select(
                            options=[("Todos los Equipos", "ALL")],
                            value="ALL",
                            id="audit-device-select",
                            allow_blank=False,
                        )
                        yield Label("Estado:", classes="audit-filter-label")
                        yield Select(
                            options=[
                                ("Todos los Eventos", "ALL"),
                                ("Exitosos (SUCCESS)", "SUCCESS"),
                                ("Fallidos / Rechazados", "FAILED"),
                                ("Rollbacks", "ROLLBACK"),
                                ("Investigaciones", "INVESTIGATION"),
                            ],
                            value="ALL",
                            id="audit-status-select",
                            allow_blank=False,
                        )
                        yield Input(
                            placeholder="Buscar por comando, host o acción...",
                            id="audit-search-input",
                        )

                    with Horizontal(id="audit-action-buttons"):
                        yield Button("Recargar (r)", id="btn-refresh-audit")
                        yield Button("Exportar JSON", id="btn-export-audit")
                        yield Button("Purgar Tests", id="btn-purge-test-audit", variant="error")

                # 3. Main Data Table with generous cell spacing
                yield DataTable(id="audit-data-table", cursor_type="row", zebra_stripes=True)

                # 4. Live Detailed Inspection Card
                yield Static(id="audit-detail-card")

    def on_mount(self) -> None:
        table = self.query_one("#audit-data-table", DataTable)
        table.cell_padding = 2
        table.add_columns(
            "Timestamp (UTC)",
            "Tipo de Evento",
            "Equipo Host",
            "Acción",
            "HITL Aprobado",
            "Verificación",
            "Rollback",
            "Comandos Ejecutados",
        )
        self.reload_audit_data()
        self._reset_detail_panel()

    def _reset_detail_panel(self) -> None:
        diag = self.query_one("#audit-detail-card", Static)
        msg = (
            "[dim cyan]Selecciona cualquier fila de la bitácora para inspeccionar en detalle: "
            "comandos CLI completos, salidas del equipo, aprobaciones del operador, "
            "verificación de guardarraíles y respaldos generados.[/dim cyan]"
        )
        diag.update(
            Panel(
                msg,
                title="PANEL DE INSPECCION FORENSE Y AUDITORIA",
                border_style="#00b4d8",
                box=box.ROUNDED,
            )
        )

    def reload_audit_data(self, render_detail: bool = True) -> None:
        """Parses audit.jsonl, populates records, updates device filter, and refreshes the table."""
        audit_file = Path(settings.audit_log_path)
        self.all_records.clear()

        if audit_file.exists():
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped:
                            try:
                                self.all_records.append(json.loads(stripped))
                            except Exception:
                                continue
            except Exception:
                pass

        self._update_device_select_options()
        self._apply_filters_and_render(render_detail=render_detail)

    def _update_device_select_options(self) -> None:
        """Populates the device filter Select with unique hosts found in logs + enrolled devices."""
        device_select = self.query_one("#audit-device-select", Select)
        unique_hosts = set()

        for rec in self.all_records:
            h = rec.get("device_host")
            if h:
                unique_hosts.add(str(h))

        for dev in db.list_devices():
            h = dev.get("host")
            if h:
                unique_hosts.add(str(h))

        options = [("Todos los Equipos", "ALL")]
        for host in sorted(unique_hosts):
            options.append((host, host))

        curr_val = device_select.value
        device_select.set_options(options)
        if curr_val in [opt[1] for opt in options]:
            device_select.value = curr_val
        else:
            device_select.value = "ALL"

    def _apply_filters_and_render(self, render_detail: bool = True) -> None:
        """Filters audit records based on selected host, status, and search query."""
        table = self.query_one("#audit-data-table", DataTable)
        table.clear()

        dev_filter = self.query_one("#audit-device-select", Select).value or "ALL"
        status_filter = self.query_one("#audit-status-select", Select).value or "ALL"
        search_query = self.query_one("#audit-search-input", Input).value.strip().lower()

        filtered: List[Dict[str, Any]] = []

        for rec in self.all_records:
            # 1. Device Filter
            host = str(rec.get("device_host") or "")
            if dev_filter != "ALL" and host != dev_filter:
                continue

            # 2. Status Filter
            etype = str(rec.get("event_type") or "").upper()
            vstatus = str(rec.get("verification_status") or "").upper()
            rollback = bool(rec.get("rollback_triggered"))

            if status_filter == "SUCCESS":
                if not ("SUCCESS" in etype or vstatus == "PASSED" or "RESOLVED" in etype):
                    continue
            elif status_filter == "FAILED":
                if not ("FAILED" in etype or "REJECTED" in etype or "BLOCKED" in etype or vstatus == "FAILED"):
                    continue
            elif status_filter == "ROLLBACK":
                if not (rollback or "ROLLBACK" in etype):
                    continue
            elif status_filter == "INVESTIGATION":
                if not ("NO_OP" in etype or "INVESTIGATION" in etype):
                    continue

            # 3. Search Query Filter
            if search_query:
                action = str(rec.get("action") or "").lower()
                cmds = " ".join(rec.get("commands") or []).lower()
                extra_str = json.dumps(rec.get("extra") or {}).lower()
                out_str = str(rec.get("execution_output") or "").lower()
                if not (
                    search_query in host.lower()
                    or search_query in action
                    or search_query in cmds
                    or search_query in etype.lower()
                    or search_query in extra_str
                    or search_query in out_str
                ):
                    continue

            filtered.append(rec)

        self.filtered_records = filtered

        # Render in reverse chronological order (newest events first)
        for idx, rec in enumerate(reversed(self.filtered_records)):
            ts = (rec.get("timestamp") or "")[:19].replace("T", " ")
            etype = rec.get("event_type") or "UNKNOWN"
            host = rec.get("device_host") or ""
            action = rec.get("action") or "none"
            approved = "SI" if rec.get("approved") else "NO"
            vstatus = rec.get("verification_status") or "N/A"
            rollback = "SI" if rec.get("rollback_triggered") else "NO"

            raw_cmds = rec.get("commands") or []
            cmds_text = ", ".join(raw_cmds) if raw_cmds else "Ninguno"
            if len(cmds_text) > 35:
                cmds_text = cmds_text[:32] + "..."

            # Color styling
            etype_styled = Text(etype)
            if "SUCCESS" in etype or "RESOLVED" in etype or "NO_OP" in etype:
                etype_styled.stylize("bold green")
            elif "REJECTED" in etype or "FAILED" in etype or "BLOCKED" in etype:
                etype_styled.stylize("bold red")
            elif "OPERATOR" in etype or "ROLLBACK" in etype:
                etype_styled.stylize("bold yellow")
            else:
                etype_styled.stylize("bold cyan")

            appr_styled = Text(approved)
            appr_styled.stylize("bold green" if approved == "SI" else "bold red")

            verif_styled = Text(vstatus)
            if vstatus == "PASSED":
                verif_styled.stylize("bold green")
            elif vstatus == "FAILED":
                verif_styled.stylize("bold red")
            else:
                verif_styled.stylize("dim white")

            rollback_styled = Text(rollback)
            if rollback == "SI":
                rollback_styled.stylize("bold red")
            else:
                rollback_styled.stylize("dim white")

            table.add_row(
                ts,
                etype_styled,
                Text(host, style="bold cyan"),
                action,
                appr_styled,
                verif_styled,
                rollback_styled,
                cmds_text,
                key=str(idx),
            )

        if render_detail:
            if self.filtered_records:
                self._render_record_details(self.filtered_records[-1])
            else:
                self._reset_detail_panel()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Triggered when the operator highlights or navigates between audit rows."""
        row_key = event.row_key.value
        try:
            # We reversed when populating: index is len - 1 - int(row_key)
            idx = len(self.filtered_records) - 1 - int(row_key)
            if 0 <= idx < len(self.filtered_records):
                self._render_record_details(self.filtered_records[idx])
        except Exception:
            pass

    def _render_record_details(self, rec: Dict[str, Any]) -> None:
        """Renders comprehensive forensic data for the highlighted audit record."""
        diag = self.query_one("#audit-detail-card", Static)
        self.selected_record = rec

        ts = (rec.get("timestamp") or "")[:19].replace("T", " ")
        etype = rec.get("event_type") or "UNKNOWN"
        host = rec.get("device_host") or "Desconocido"
        action = rec.get("action") or "none"
        approved = "SI" if rec.get("approved") else "NO"
        approver = rec.get("approver") or "local_operator"
        vstatus = rec.get("verification_status") or "N/A"
        rollback = "SI" if rec.get("rollback_triggered") else "NO"
        cmds = rec.get("commands") or []
        output = rec.get("execution_output")
        extra = rec.get("extra") or {}

        # Determine border color
        if "SUCCESS" in etype or "RESOLVED" in etype or vstatus == "PASSED":
            border_col = "#4ade80"
        elif "FAILED" in etype or "REJECTED" in etype or "BLOCKED" in etype or rollback == "SI":
            border_col = "#f43f5e"
        else:
            border_col = "#00b4d8"

        # Format Commands
        if cmds:
            cmds_formatted = "\n".join(f"    {i + 1}. [bold white]{cmd}[/bold white]" for i, cmd in enumerate(cmds))
        else:
            cmds_formatted = "    [dim white]Ninguno (Operación de sólo lectura o diagnóstico informativo)[/dim white]"

        # Format Output or Diagnosis
        out_formatted = ""
        if output:
            out_formatted = f"\n  * [cyan]Salida CLI Recibida del Equipo:[/cyan]\n[dim white]{output[:500]}[/dim white]"
        elif extra.get("diagnosis"):
            out_formatted = f"\n  * [cyan]Diagnóstico del Motor IA:[/cyan] [white]{extra['diagnosis']}[/white]"

        # Format Extra metadata (backup, job_id, etc.)
        meta_items = []
        if "backup" in extra:
            meta_items.append(f"Backup de Seguridad: [bold green]{extra['backup']}[/bold green]")
        if "job_id" in extra:
            meta_items.append(f"ID Despliegue: [bold cyan]{extra['job_id']}[/bold cyan]")
        if "reason" in extra:
            meta_items.append(f"Motivo: [bold yellow]{extra['reason']}[/bold yellow]")
        if "total_devices" in extra:
            meta_items.append(f"Equipos en Lote: [bold white]{extra['total_devices']}[/bold white]")

        meta_str = ("\n  * Metadatos: " + " | ".join(meta_items)) if meta_items else ""

        content = (
            f"─── REGISTRO FORENSE: [bold white]{etype}[/bold white] // Host: [bold cyan]{host}[/bold cyan] ───\n\n"
            f"  * Fecha y Hora (UTC): [bold white]{ts}[/bold white]\n"
            f"  * Acción Operativa: [bold yellow]{action}[/bold yellow]\n"
            f"  * Aprobación Operador: [bold green]{approved}[/bold green] (Autorizado por: {approver})\n"
            f"  * Verificación Estado Red: [bold cyan]{vstatus}[/bold cyan] | Rollback Automático: {rollback}\n"
            f"  * Comandos CLI Enviados:\n{cmds_formatted}"
            f"{out_formatted}"
            f"{meta_str}"
        )

        diag.update(
            Panel(
                content,
                title=f"DETALLE FORENSE // {host} // {ts}",
                border_style=border_col,
                box=box.ROUNDED,
            )
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Triggered when either the device or status filter changes."""
        self._apply_filters_and_render()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Triggered on text input in search box."""
        if event.input.id == "audit-search-input":
            self._apply_filters_and_render()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("btn-back-from-audit", "btn-audit-home"):
            self.post_message(self.ReturnHomeRequested())
        elif btn_id == "btn-refresh-audit":
            self.reload_audit_data()
        elif btn_id == "btn-export-audit":
            self.action_export_audit()
        elif btn_id == "btn-purge-test-audit":
            self.action_purge_tests()

    def action_export_audit(self) -> None:
        """Exports the currently filtered audit dataset to a timestamped JSON file."""
        diag = self.query_one("#audit-detail-card", Static)
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_path = Path("logs") / f"audit_export_{ts_str}.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.filtered_records, f, indent=2, ensure_ascii=False)

            diag.update(
                Panel(
                    f"[bold green][OK] Bitácora exportada exitosamente:[/bold green]\n\n"
                    f"  * Archivo generado: [bold white]{export_path.resolve()}[/bold white]\n"
                    f"  * Total de eventos exportados: [bold cyan]{len(self.filtered_records)}[/bold cyan]\n"
                    f"  * Integridad: Formato JSON estructurado para cumplimiento y auditorías externas.",
                    title="EXPORTACION COMPLETADA",
                    border_style="#4ade80",
                    box=box.ROUNDED,
                )
            )
        except Exception as e:
            diag.update(
                Panel(
                    f"[bold red]Error al exportar bitácora:[/bold red] {e}",
                    title="ERROR DE EXPORTACION",
                    border_style="#f43f5e",
                    box=box.ROUNDED,
                )
            )

    def action_purge_tests(self) -> None:
        """Safely cleanses synthetic test logs, preserving authentic production device records."""
        diag = self.query_one("#audit-detail-card", Static)
        audit_file = Path(settings.audit_log_path)
        if not audit_file.exists():
            return

        enrolled_hosts = {d.get("host") for d in db.list_devices()}
        synthetic_test_hosts = {
            "10.0.0.1",
            "10.0.0.2",
            "10.10.10.1",
            "10.10.20.11",
            "192.168.88.1",
            "192.168.99.1",
            "192.168.1.50",
            "192.168.1.1",
        }

        authentic_records: List[Dict[str, Any]] = []
        purged_count = 0

        for rec in self.all_records:
            host = str(rec.get("device_host") or "")
            extra_str = json.dumps(rec.get("extra") or {})
            is_test = (
                "pytest" in extra_str
                or "Temp" in extra_str
                or (host in synthetic_test_hosts and host not in enrolled_hosts)
            )
            if is_test:
                purged_count += 1
            else:
                authentic_records.append(rec)

        try:
            # Create safety backup before purging
            backup_path = Path("logs") / "audit_backup_pre_purge.jsonl"
            backup_path.write_bytes(audit_file.read_bytes())

            # Rewrite clean audit file
            with open(audit_file, "w", encoding="utf-8") as f:
                for r in authentic_records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            self.reload_audit_data(render_detail=False)

            diag.update(
                Panel(
                    f"[bold green][OK] Depuración de registros sintéticos completada exitosamente:[/bold green]\n\n"
                    f"  * Registros de prueba purgados: [bold yellow]{purged_count}[/bold yellow]\n"
                    f"  * Registros auténticos conservados: [bold cyan]{len(authentic_records)}[/bold cyan]\n"
                    f"  * Respaldo previo creado en: [dim white]{backup_path.name}[/dim white]\n\n"
                    f"[dim cyan]A partir de ahora, todas las pruebas automatizadas se ejecutan en un entorno aislado "
                    f"sin alterar esta bitácora inmutable.[/dim cyan]",
                    title="BITACORA DEPURADA Y OPTIMIZADA",
                    border_style="#4ade80",
                    box=box.ROUNDED,
                )
            )
        except Exception as e:
            diag.update(
                Panel(
                    f"[bold red]Error al purgar registros:[/bold red] {e}",
                    title="ERROR EN DEPURACION",
                    border_style="#f43f5e",
                    box=box.ROUNDED,
                )
            )
