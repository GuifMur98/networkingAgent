"""Unit tests for Network OS Drivers."""

from networking_agent.drivers.cisco_ios import CiscoIOSDriver
from networking_agent.drivers.cisco_nxos import CiscoNXOSDriver
from networking_agent.drivers.juniper import JuniperJunosDriver
from networking_agent.drivers.mikrotik import MikrotikRouterOSDriver
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


def test_mikrotik_routeros_driver_generates_correct_cli():
    dev = DeviceInventory(host="192.168.88.1", device_type="mikrotik_routeros")
    driver = MikrotikRouterOSDriver(dev)

    # Test interface disable
    intent_disable = NetworkIntent(
        diagnosis="Interface looping",
        severity="HIGH",
        requires_config_change=True,
        action="disable_interface",
        target_interface="ether2",
    )
    assert driver.build_candidate_commands(intent_disable) == ['/interface set [find name="ether2"] disabled=yes']

    # Test MTU set
    intent_mtu = NetworkIntent(
        diagnosis="MTU fragmentation",
        severity="MEDIUM",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="ether1",
        mtu_value=9000,
    )
    assert driver.build_candidate_commands(intent_mtu) == ['/interface set [find name="ether1"] mtu=9000']

    # Test BGP neighbor reset
    intent_bgp = NetworkIntent(
        diagnosis="BGP neighbor hung",
        severity="CRITICAL",
        requires_config_change=True,
        action="reset_bgp_neighbor",
        bgp_neighbor_ip="10.255.0.1",
    )
    assert driver.build_candidate_commands(intent_bgp) == [
        '/routing bgp connection disable [find remote.address="10.255.0.1"]',
        '/routing bgp connection enable [find remote.address="10.255.0.1"]',
    ]
    assert driver.get_running_config_command() == "/export verbose=no"


def test_proactive_remediations_across_drivers():
    cisco_dev = DeviceInventory(host="10.0.0.1", device_type="cisco_ios")
    cisco_driver = CiscoIOSDriver(cisco_dev)

    # Duplex full remediation on Cisco
    duplex_intent = NetworkIntent(
        diagnosis="Packet loss due to half-duplex mismatch on LAN interface",
        severity="HIGH",
        requires_config_change=True,
        action="set_interface_duplex_full",
        target_interface="GigabitEthernet1/0/2",
    )
    assert cisco_driver.build_candidate_commands(duplex_intent) == [
        "interface GigabitEthernet1/0/2",
        "speed auto",
        "duplex full",
    ]

    # Restart interface on MikroTik
    mikro_dev = DeviceInventory(host="192.168.88.1", device_type="mikrotik_routeros")
    mikro_driver = MikrotikRouterOSDriver(mikro_dev)

    restart_intent = NetworkIntent(
        diagnosis="Interface hung, resetting link",
        severity="MEDIUM",
        requires_config_change=True,
        action="restart_interface",
        target_interface="ether2",
    )
    assert mikro_driver.build_candidate_commands(restart_intent) == [
        '/interface set [find name="ether2"] disabled=yes',
        '/interface set [find name="ether2"] disabled=no',
    ]
