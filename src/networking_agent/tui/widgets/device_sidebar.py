"""Device inventory sidebar with platform badges and registration action."""

from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView

from networking_agent.core.db import db
from networking_agent.models.device import DeviceInventory


class DeviceSidebar(Widget):
    """Sidebar widget managing the device inventory navigation."""

    DEFAULT_CSS = """
    DeviceSidebar {
        width: 32;
        height: 100%;
        background: #161b22;
        border-right: solid #30363d;
        padding: 1;
    }
    """

    class DeviceSelected(Message):
        """Emitted when the operator chooses a device."""

        def __init__(self, device: DeviceInventory):
            super().__init__()
            self.device = device

    class AddDeviceRequested(Message):
        """Emitted when the operator clicks the add device button."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices: List[DeviceInventory] = []
        self.selected_device: Optional[DeviceInventory] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-container"):
            yield Label("INVENTARIO DE RED", id="sidebar-title")
            yield ListView(id="device-list")
            yield Button("+ Registrar Equipo", id="btn-add-device", variant="primary")

    def on_mount(self) -> None:
        self.reload_devices()

    def reload_devices(self) -> None:
        """Fetch devices from SQLite inventory and refresh the ListView."""
        self.devices = db.list_device_inventories()
        list_view = self.query_one("#device-list", ListView)
        list_view.clear()

        for dev in self.devices:
            vendor_badge = dev.device_type
            badge_color = "cyan"
            if "cisco" in dev.device_type:
                badge_color = "bright_blue"
                vendor_badge = "Cisco"
            elif "juniper" in dev.device_type:
                badge_color = "magenta"
                vendor_badge = "Juniper"
            elif "mikrotik" in dev.device_type:
                badge_color = "green"
                vendor_badge = "MikroTik"

            label_text = Text()
            label_text.append(f"{dev.host}\n", style="bold white")
            label_text.append(f"[{vendor_badge}]", style=f"bold {badge_color}")
            label_text.append(f" :{dev.port} ({dev.username})", style="dim")

            item = ListItem(Label(label_text), classes="device-item")
            item.device_data = dev  # type: ignore[attr-defined]
            list_view.append(item)

        if self.devices:
            if not self.selected_device or self.selected_device not in self.devices:
                self.selected_device = self.devices[0]
                self.post_message(self.DeviceSelected(self.selected_device))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection of a device in the list."""
        if hasattr(event.item, "device_data"):
            dev: DeviceInventory = event.item.device_data  # type: ignore[attr-defined]
            self.selected_device = dev
            self.post_message(self.DeviceSelected(dev))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add-device":
            self.post_message(self.AddDeviceRequested())
