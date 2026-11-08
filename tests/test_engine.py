"""Unit tests for the Closed-Loop Orchestration Engine."""

import pytest

from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.models.config_intent import ConfigurationIntent, ProtocolConfigType
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


def test_agent_proactive_symptom_investigation(mocker, tmp_path):
    # Mock AI brain returning packet loss root cause diagnosis
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis="Packet loss detected on ether2 due to half-duplex mismatch. Forcing full duplex.",
        severity="HIGH",
        requires_config_change=True,
        action="set_interface_duplex_full",
        target_interface="ether2",
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    mock_driver = mocker.MagicMock()
    mock_driver.build_candidate_commands.return_value = [
        '/interface ethernet set [find name="ether2"] auto-negotiation=yes full-duplex=yes'
    ]
    mock_driver.run_health_check.return_value = {
        "/interface print stats": "ether2: rx-drop=4500 tx-drop=1200 rx-error=800",
    }
    mock_driver.backup_running_config.return_value = tmp_path / "mock_mikrotik_backup.cfg"
    mock_driver.execute_commands.return_value = "Command executed."
    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True)
    dev = DeviceInventory(host="192.168.88.1", device_type="mikrotik_routeros")
    event = TelemetryEvent(
        raw_text="El router presenta pérdidas del 25% y lentitud en la LAN conectada a ether2.",
        source_host=dev.host,
    )

    result = agent.process_telemetry(device=dev, telemetry=event, mode="PROACTIVE")
    assert result is True
    # In PROACTIVE mode, run_health_check is called for live diagnostics, pre-check, and post-check
    assert mock_driver.run_health_check.call_count >= 2
    assert mock_brain.analyze_event.called
    # Check that the prompt sent to the brain contains the user symptom and live telemetry
    sent_prompt = mock_brain.analyze_event.call_args[0][0]
    assert "OPERATIONAL SYMPTOM REPORTED BY OPERATOR" in sent_prompt
    assert "LIVE DEVICE DIAGNOSTIC TELEMETRY" in sent_prompt
    assert "Protected WAN / Gateway / Management Interfaces" in sent_prompt


def test_agent_blocks_wan_restart_attempt(mocker):
    # Simulated scenario where AI erroneously attempts to bounce ether1 (WAN)
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis="High link flapping on ether1 (44 link-downs). Restarting interface.",
        severity="MEDIUM",
        requires_config_change=True,
        action="restart_interface",
        target_interface="ether1",
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    mock_driver = mocker.MagicMock()
    mock_driver.get_gateway_interfaces.return_value = ["ether1", "wan", "uplink"]
    mock_driver.run_health_check.return_value = {"/interface print stats": "link-downs=44"}
    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True)
    dev = DeviceInventory(host="192.168.99.1", device_type="mikrotik_routeros")
    event = TelemetryEvent(
        raw_text="siento lento el internet y cuesta mucho abrir paginas",
        source_host=dev.host,
    )

    result = agent.process_telemetry(device=dev, telemetry=event, mode="PROACTIVE")
    # Must be intercepted by Blast Radius guard and blocked!
    assert result is False
    # Ensure commands were never built or executed on the device
    assert not mock_driver.execute_commands.called


@pytest.mark.parametrize(
    "vendor,device_type,mgmt_iface",
    [
        ("Cisco IOS", "cisco_ios", "GigabitEthernet0/0/0"),
        ("Cisco NX-OS", "cisco_nxos", "mgmt0"),
        ("Juniper Junos", "juniper_junos", "fxp0"),
    ],
)
def test_agent_blocks_multi_vendor_management_loss(mocker, vendor, device_type, mgmt_iface):
    # Tests that across Cisco, Juniper, etc., any attempt to bounce management interfaces is blocked
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis=f"Flapping detected on {mgmt_iface}. Restarting.",
        severity="CRITICAL",
        requires_config_change=True,
        action="restart_interface",
        target_interface=mgmt_iface,
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True)
    dev = DeviceInventory(host="10.10.10.1", device_type=device_type)
    event = TelemetryEvent(raw_text=f"Interface flap on {mgmt_iface}", source_host=dev.host)

    result = agent.process_telemetry(device=dev, telemetry=event)
    assert result is False


def test_agent_hitl_operator_rejection_protects_device(mocker):
    mock_brain = mocker.MagicMock()
    mock_brain.analyze_event.return_value = NetworkIntent(
        diagnosis="Safe MTU change on access port",
        severity="LOW",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="Ethernet1/10",
        mtu_value=9000,
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    mock_driver = mocker.MagicMock()
    mock_driver.build_candidate_commands.return_value = ["interface Ethernet1/10", "mtu 9000"]
    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    # Operator explicitly types 'n' to reject
    mocker.patch("rich.prompt.Prompt.ask", return_value="n")

    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=False)
    dev = DeviceInventory(host="10.10.20.11", device_type="cisco_nxos")
    event = TelemetryEvent(raw_text="MTU discrepancy", source_host=dev.host)

    result = agent.process_telemetry(device=dev, telemetry=event)
    assert result is False
    assert not mock_driver.execute_commands.called


def test_agent_execute_configuration_with_running_config_and_conflict_check(mocker, tmp_path):
    mock_brain = mocker.MagicMock()
    mock_brain.synthesize_configuration.return_value = ConfigurationIntent(
        protocol_type=ProtocolConfigType.OSPF,
        description="Integración de subred en proceso OSPF 1",
        target_host="192.168.1.1",
        candidate_commands=["router ospf 1", "network 10.50.0.0 0.0.0.255 area 0"],
        verification_commands=["show ip ospf neighbor"],
        rollback_commands=["router ospf 1", "no network 10.50.0.0 0.0.0.255 area 0"],
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    mock_driver = mocker.MagicMock()
    mock_driver.get_running_config.return_value = (
        "router ospf 1\n network 192.168.1.0 0.0.0.255 area 0\ninterface Gi0/1\n ip address 192.168.1.1 255.255.255.0\n"
    )
    mock_driver.backup_running_config.return_value = tmp_path / "pre_change_backup.cfg"
    mock_driver.execute_commands.return_value = "Applied OK"
    mock_driver.get_rollback_description.return_value = "Rollback available"
    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    mock_observer = mocker.MagicMock()
    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True, observer=mock_observer)
    dev = DeviceInventory(host="192.168.1.1", device_type="cisco_ios")

    intent = agent.execute_configuration(
        device=dev,
        natural_request="agrega la red 10.50.0.0/24 al enrutamiento dinamico",
    )
    assert intent is not None
    assert intent.protocol_type == ProtocolConfigType.OSPF
    assert "[OK]" in intent.conflict_analysis
    assert "OSPF" in intent.conflict_analysis
    assert mock_driver.get_running_config.called
    assert mock_driver.execute_commands.called
    assert mock_observer.on_progress.called


def test_agent_execute_configuration_detects_ip_overlap(mocker, tmp_path):
    mock_brain = mocker.MagicMock()
    mock_brain.synthesize_configuration.return_value = ConfigurationIntent(
        protocol_type=ProtocolConfigType.CUSTOM,
        description="Asignación de IP en interfaz Gi0/2",
        target_host="192.168.1.1",
        candidate_commands=[
            "interface GigabitEthernet0/2",
            "ip address 192.168.1.50 255.255.255.0",
        ],
        verification_commands=["show ip interface brief"],
        rollback_commands=["interface GigabitEthernet0/2", "no ip address"],
    )
    mocker.patch("networking_agent.engine.agent.get_ai_brain", return_value=mock_brain)

    mock_driver = mocker.MagicMock()
    # Running config already has 192.168.1.1/24 on Gi0/1
    mock_driver.get_running_config.return_value = (
        "interface GigabitEthernet0/1\n ip address 192.168.1.1 255.255.255.0\n"
    )
    mock_driver.backup_running_config.return_value = tmp_path / "pre_change_backup.cfg"
    mock_driver.execute_commands.return_value = "Applied OK"
    mock_driver.get_rollback_description.return_value = "Rollback available"
    mocker.patch("networking_agent.engine.agent.get_os_driver", return_value=mock_driver)

    mock_observer = mocker.MagicMock()
    agent = NetworkAssistantAgent(ai_provider="ollama", auto_approve=True, observer=mock_observer)
    dev = DeviceInventory(host="192.168.1.1", device_type="cisco_ios")

    intent = agent.execute_configuration(
        device=dev,
        natural_request="asigna la ip 192.168.1.50 a Gi0/2",
    )
    assert intent is not None
    assert "[!] Conflicto detectado" in intent.conflict_analysis
    assert "GigabitEthernet0/1" in intent.conflict_analysis


