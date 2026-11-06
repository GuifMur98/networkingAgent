"""Unit tests for Network OS Drivers."""

from networking_agent.drivers.cisco_ios import CiscoIOSDriver
from networking_agent.drivers.cisco_nxos import CiscoNXOSDriver
from networking_agent.drivers.juniper import JuniperJunosDriver
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


def test_cisco_ios_driver_generates_correct_cli():
    dev = DeviceInventory(host="10.1.1.1", device_type="cisco_ios")
    driver = CiscoIOSDriver(dev)

    intent = NetworkIntent(
        diagnosis="Interface down",
        severity="HIGH",
        requires_config_change=True,
        action="enable_interface",
        target_interface="GigabitEthernet1/0/1",
    )
    cmds = driver.build_candidate_commands(intent)
    assert cmds == ["interface GigabitEthernet1/0/1", "no shutdown"]


def test_cisco_nxos_driver_generates_transactional_cli():
    dev = DeviceInventory(host="10.1.1.2", device_type="cisco_nxos")
    driver = CiscoNXOSDriver(dev)

    intent = NetworkIntent(
        diagnosis="MTU mismatch",
        severity="MEDIUM",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="Ethernet1/1",
        mtu_value=9216,
    )
    cmds = driver.build_candidate_commands(intent)
    assert cmds == [
        "configure session AI_AGENT_FIX",
        "interface Ethernet1/1",
        "mtu 9216",
        "commit",
    ]


def test_juniper_junos_driver_generates_commit_confirmed():
    dev = DeviceInventory(host="10.1.1.3", device_type="juniper_junos")
    driver = JuniperJunosDriver(dev)

    intent = NetworkIntent(
        diagnosis="Disable interface",
        severity="HIGH",
        requires_config_change=True,
        action="disable_interface",
        target_interface="ge-0/0/0",
    )
    cmds = driver.build_candidate_commands(intent)
    assert cmds == [
        "set interfaces ge-0/0/0 disable",
        "commit confirmed 3",
    ]
