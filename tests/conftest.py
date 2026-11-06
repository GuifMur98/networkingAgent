"""Pytest configuration and shared test fixtures."""

import pytest
from pydantic import SecretStr

from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


@pytest.fixture
def sample_device_nxos() -> DeviceInventory:
    return DeviceInventory(
        host="10.10.20.11",
        device_type="cisco_nxos",
        username="netadmin",
        password=SecretStr("supersecret123"),
    )


@pytest.fixture
def sample_device_ios() -> DeviceInventory:
    return DeviceInventory(
        host="10.10.10.1",
        device_type="cisco_ios",
        username="netadmin",
        password=SecretStr("supersecret123"),
    )


@pytest.fixture
def sample_valid_intent() -> NetworkIntent:
    return NetworkIntent(
        diagnosis="MTU mismatch detected on interface Ethernet1/1 preventing OSPF full adjacency.",
        severity="HIGH",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="Ethernet1/1",
        mtu_value=9216,
    )
