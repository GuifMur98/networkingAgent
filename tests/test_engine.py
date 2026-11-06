"""Unit tests for the Closed-Loop Orchestration Engine."""

from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.models.telemetry import TelemetryEvent


def test_agent_handles_no_op_event(mocker):
    # Mock AI brain returning no config change required
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis="Normal info event, no action needed.",
        severity="LOW",
        requires_config_change=False,
        action="none",
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    agent = NetworkAssistantAgent(ai_provider="ollama")
    dev = DeviceInventory(host="10.0.0.1", device_type="cisco_ios")
    event = TelemetryEvent(raw_text="%SYS-5-CONFIG_I: Configured from console by admin")

    result = agent.process_telemetry(device=dev, telemetry=event)
    assert result is True


def test_agent_closed_loop_execution_success(mocker, tmp_path):
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis="MTU mismatch on leaf port",
        severity="HIGH",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="Ethernet1/1",
        mtu_value=9216,
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    # Mock Driver
    mock_driver = mocker.MagicMock()
    mock_driver.build_candidate_commands.return_value = [
        "configure session AI_AGENT_FIX",
        "interface Ethernet1/1",
        "mtu 9216",
        "commit",
    ]
    mock_driver.run_health_check.return_value = {"show interface status err-disabled": "No err-disabled"}
    mock_driver.backup_running_config.return_value = tmp_path / "mock_backup.cfg"
    mock_driver.execute_commands.return_value = "Commit successful."

    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True)
    dev = DeviceInventory(host="10.10.20.11", device_type="cisco_nxos")
    event = TelemetryEvent(raw_text="OSPF MTU mismatch")

    result = agent.process_telemetry(device=dev, telemetry=event)
    assert result is True
    assert mock_driver.backup_running_config.called
    assert mock_driver.execute_commands.called
    assert mock_driver.run_health_check.call_count == 2  # Pre-check + Post-check
