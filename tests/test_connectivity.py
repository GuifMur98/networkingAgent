"""Tests for network connectivity engine and DeviceInventoryView reachability actions."""

import socket
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static

from networking_agent.engine.connectivity import (
    ConnectivityTester,
    DeviceConnectivityReport,
    PingResult,
    PortResult,
)
from networking_agent.models.device import DeviceInventory
from networking_agent.tui.widgets.device_inventory_view import DeviceInventoryView


@pytest.mark.anyio
async def test_ping_success():
    fake_stdout = (
        b"Respuesta desde 192.168.1.40: bytes=32 tiempo=4ms TTL=64\n"
        b"Paquetes: enviados = 2, recibidos = 2, perdidos = 0 (0% perdidos)\n"
        b"Minimo = 3ms, Maximo = 5ms, Media = 4ms"
    )
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_stdout, b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result: PingResult = await ConnectivityTester.ping("192.168.1.40", count=2)
        assert result.is_reachable is True
        assert result.packet_loss == "0%"
        assert "ms" in result.rtt_avg


@pytest.mark.anyio
async def test_ping_failure():
    fake_stdout = b"Host de destino inaccesible.\nPaquetes: enviados = 2, recibidos = 0, perdidos = 2 (100% perdidos)"
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (fake_stdout, b"")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result: PingResult = await ConnectivityTester.ping("192.168.1.99", count=2)
        assert result.is_reachable is False
        assert result.packet_loss == "100%"


@pytest.mark.anyio
async def test_ping_invalid_host():
    result = await ConnectivityTester.ping("invalid host; evil")
    assert result.is_reachable is False
    assert result.packet_loss == "100%"


@pytest.mark.anyio
async def test_check_port_open():
    with patch.object(socket.socket, "connect", return_value=None):
        result: PortResult = await ConnectivityTester.check_port("192.168.1.40", 22)
        assert result.is_open is True
        assert result.elapsed_ms is not None


@pytest.mark.anyio
async def test_check_port_closed():
    with patch.object(socket.socket, "connect", side_effect=OSError("Connection refused")):
        result: PortResult = await ConnectivityTester.check_port("192.168.1.40", 22)
        assert result.is_open is False
        assert "Connection refused" in (result.error or "")


@pytest.mark.anyio
async def test_full_device_connectivity():
    ping_mock = PingResult(host="192.168.1.40", is_reachable=True, rtt_avg="3ms", packet_loss="0%")
    port_mock = PortResult(host="192.168.1.40", port=22, is_open=True, elapsed_ms=4, error=None)

    with patch.object(ConnectivityTester, "ping", return_value=ping_mock):
        with patch.object(ConnectivityTester, "check_port", return_value=port_mock):
            device = DeviceInventory(
                host="192.168.1.40",
                device_type="cisco_ios",
                username="admin",
                port=22,
            )
            report: DeviceConnectivityReport = await ConnectivityTester.run_full_diagnosis(device)
            assert report.is_online is True
            assert report.ping.is_reachable is True
            assert report.tcp_port.is_open is True


class InventoryTestApp(App):
    def compose(self) -> ComposeResult:
        yield DeviceInventoryView(id="device-inventory")


@pytest.mark.anyio
async def test_inventory_view_tui_interactions():
    fake_list = [
        {
            "id": 1,
            "name": "CORE-SW01",
            "host": "192.168.1.10",
            "device_type": "cisco_ios",
            "port": 22,
            "username": "admin",
        },
        {
            "id": 2,
            "name": "EDGE-RTR01",
            "host": "192.168.1.1",
            "device_type": "mikrotik_routeros",
            "port": 22,
            "username": "admin",
        },
    ]
    dev1 = DeviceInventory(
        host="192.168.1.10",
        device_type="cisco_ios",
        username="admin",
        port=22,
    )

    with patch("networking_agent.tui.widgets.device_inventory_view.db.list_devices", return_value=fake_list):
        with patch("networking_agent.tui.widgets.device_inventory_view.db.get_device_by_id", return_value=dev1):
            app = InventoryTestApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                table = app.query_one("#inventory-data-table", DataTable)
                assert table.row_count == 2
                assert table.cell_padding == 2

                diag = app.query_one("#inventory-diagnostic-card", Static)
                assert diag is not None

                # Test Ping Button Action
                ping_btn = app.query_one("#btn-inv-ping")
                with patch.object(
                    ConnectivityTester,
                    "ping",
                    return_value=PingResult(
                        host="192.168.1.10",
                        is_reachable=True,
                        rtt_avg="2ms",
                        packet_loss="0%",
                    ),
                ):
                    ping_btn.press()
                    await pilot.pause()
                    card_text = str(getattr(diag.content, "renderable", diag.content))
                    assert "ALCANZABLE" in card_text

                # Test SSH Port Button Action
                port_btn = app.query_one("#btn-inv-test-conn")
                with patch.object(
                    ConnectivityTester,
                    "check_port",
                    return_value=PortResult(
                        host="192.168.1.10",
                        port=22,
                        is_open=True,
                        elapsed_ms=3,
                        error=None,
                    ),
                ):
                    port_btn.press()
                    await pilot.pause()
                    card_text = str(getattr(diag.content, "renderable", diag.content))
                    assert "ABIERTO" in card_text
