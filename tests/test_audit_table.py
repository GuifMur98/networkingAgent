"""Tests for the improved enterprise AuditTableWidget."""

import json

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Input, Select, Static

from networking_agent.core.config import settings
from networking_agent.tui.widgets.audit_table import AuditTableWidget


class AuditTestApp(App):
    def compose(self) -> ComposeResult:
        yield AuditTableWidget(id="audit-widget")


@pytest.fixture
def populated_audit_file(tmp_path):
    audit_file = tmp_path / "test_audit_data.jsonl"
    records = [
        {
            "timestamp": "2026-11-08T01:00:00+00:00",
            "event_type": "BATCH_DEPLOYMENT_SUCCESS",
            "device_host": "192.168.1.40",
            "action": "config_batch",
            "commands": ["interface vlan 100", "ip address 192.168.100.1 255.255.255.0"],
            "approved": True,
            "approver": "local_operator",
            "execution_output": "Configuration committed successfully",
            "verification_status": "PASSED",
            "rollback_triggered": False,
            "extra": {"job_id": "test-123"},
        },
        {
            "timestamp": "2026-11-08T02:00:00+00:00",
            "event_type": "GUARDRAIL_BLOCKED",
            "device_host": "10.0.0.1",
            "action": "restart_interface",
            "commands": ["shutdown"],
            "approved": False,
            "approver": "system",
            "execution_output": None,
            "verification_status": "FAILED",
            "rollback_triggered": False,
            "extra": {"reason": "Protected uplink interface"},
        },
        {
            "timestamp": "2026-11-08T03:00:00+00:00",
            "event_type": "NO_OP",
            "device_host": "192.168.1.40",
            "action": "none",
            "commands": [],
            "approved": True,
            "approver": "local_operator",
            "execution_output": None,
            "verification_status": None,
            "rollback_triggered": False,
            "extra": {"diagnosis": "Network healthy, no remediation needed"},
        },
    ]

    with open(audit_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    orig_path = settings.audit_log_path
    settings.audit_log_path = audit_file
    try:
        yield audit_file
    finally:
        settings.audit_log_path = orig_path


@pytest.mark.anyio
async def test_audit_table_mount_and_population(populated_audit_file):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#audit-data-table", DataTable)
        assert table.row_count == 3
        assert table.cell_padding == 2

        detail = app.query_one("#audit-detail-card", Static)
        assert detail is not None
        detail_text = str(getattr(detail.content, "renderable", detail.content))
        assert "192.168.1.40" in detail_text


@pytest.mark.anyio
async def test_audit_table_filtering_by_device(populated_audit_file):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#audit-data-table", DataTable)
        assert table.row_count == 3

        dev_select = app.query_one("#audit-device-select", Select)
        dev_select.value = "10.0.0.1"
        await pilot.pause()
        assert table.row_count == 1

        dev_select.value = "192.168.1.40"
        await pilot.pause()
        assert table.row_count == 2


@pytest.mark.anyio
async def test_audit_table_filtering_by_status(populated_audit_file):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#audit-data-table", DataTable)

        status_select = app.query_one("#audit-status-select", Select)
        status_select.value = "FAILED"
        await pilot.pause()
        assert table.row_count == 1

        status_select.value = "SUCCESS"
        await pilot.pause()
        assert table.row_count == 1

        status_select.value = "INVESTIGATION"
        await pilot.pause()
        assert table.row_count == 1


@pytest.mark.anyio
async def test_audit_table_search_input(populated_audit_file):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#audit-data-table", DataTable)
        search_inp = app.query_one("#audit-search-input", Input)

        search_inp.value = "vlan 100"
        await pilot.pause()
        assert table.row_count == 1

        search_inp.value = "nonexistent_query"
        await pilot.pause()
        assert table.row_count == 0


@pytest.mark.anyio
async def test_audit_table_export_json(populated_audit_file, tmp_path):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        btn_export = app.query_one("#btn-export-audit")
        btn_export.press()
        await pilot.pause()

        detail = app.query_one("#audit-detail-card", Static)
        detail_text = str(getattr(detail.content, "renderable", detail.content))
        assert "EXPORTACION COMPLETADA" in str(getattr(detail.content, "title", detail_text))


@pytest.mark.anyio
async def test_audit_table_purge_tests(populated_audit_file):
    app = AuditTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one("#audit-data-table", DataTable)
        assert table.row_count == 3

        btn_purge = app.query_one("#btn-purge-test-audit")
        btn_purge.press()
        await pilot.pause()

        # 10.0.0.1 is synthetic test host, while 192.168.1.40 is authentic
        assert table.row_count == 2
        detail = app.query_one("#audit-detail-card", Static)
        detail_text = str(getattr(detail.content, "renderable", detail.content))
        assert "192.168.1.40" in detail_text

