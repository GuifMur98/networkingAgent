"""Factory for selecting the appropriate network OS driver."""

from typing import Dict, Type

from networking_agent.drivers.base import NetworkOSDriver
from networking_agent.drivers.cisco_ios import CiscoIOSDriver
from networking_agent.drivers.cisco_nxos import CiscoNXOSDriver
from networking_agent.drivers.cisco_xr import CiscoIOSXRDriver
from networking_agent.drivers.juniper import JuniperJunosDriver
from networking_agent.models.device import DeviceInventory

DRIVER_REGISTRY: Dict[str, Type[NetworkOSDriver]] = {
    "cisco_ios": CiscoIOSDriver,
    "cisco_xe": CiscoIOSDriver,
    "cisco_nxos": CiscoNXOSDriver,
    "cisco_xr": CiscoIOSXRDriver,
    "juniper_junos": JuniperJunosDriver,
}


def get_os_driver(device: DeviceInventory) -> NetworkOSDriver:
    """Instantiates the specific driver for the device platform."""
    driver_cls = DRIVER_REGISTRY.get(device.device_type)
    if not driver_cls:
        raise ValueError(f"No driver registered for platform type: '{device.device_type}'")
    return driver_cls(device)
