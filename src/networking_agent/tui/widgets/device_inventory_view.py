"""Full device inventory management table and actions widget."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label

from networking_agent.core.db import db


class DeviceInventoryView(Widget):
    """View allowing operator to inspect, add, and delete registered devices."""

    class AddDeviceRequested(Message):
        """Emitted when the operator clicks the add device button."""

    class DeviceDeleted(Message):
        """Emitted when a device is deleted so the app can refresh counts."""

    class ReturnHomeRequested(Message):
        """Emitted when the operator wants to return to the Home/Inicio view."""

    def compose(self) -> ComposeResult:
        with Vertical(id="inventory-container"):
            with Horizontal(id="inventory-top-bar"):
                yield Label("CATALOGO DE EQUIPOS DE RED ENROLADOS", id="inventory-title")
                yield Button("[ Volver al Inicio ]", id="btn-back-from-inventory")

            yield DataTable(id="inventory-data-table", cursor_type="row", zebra_stripes=True)

            with Horizontal(classes="inventory-actions"):
                yield Button("[ + Registrar Equipo ]", id="btn-inv-add", variant="primary")
                yield Button("[ - Eliminar ]", id="btn-inv-delete", variant="error")
                yield Button("[ Recargar ]", id="btn-inv-refresh")
                yield Button("[ Volver al Inicio ]", id="btn-inv-home")

    def on_mount(self) -> None:
        table = self.query_one("#inventory-data-table", DataTable)
        table.add_columns("ID", "Nombre / Alias", "Host / IP", "Sistema Operativo", "Puerto", "Usuario SSH")
        self.reload_devices()

    def reload_devices(self) -> None:
        table = self.query_one("#inventory-data-table", DataTable)
        table.clear()
        devices = db.list_devices()

        for dev in devices:
            dev_id = str(dev.get("id", ""))
            name = dev.get("name", "")
            host = dev.get("host", "")
            os_type = dev.get("device_type", "")
            port = str(dev.get("port", 22))
            user = dev.get("username", "")

            # Color styling
            os_styled = Text(os_type)
            if "cisco" in os_type:
                os_styled.stylize("bold bright_blue")
            elif "juniper" in os_type:
                os_styled.stylize("bold magenta")
            elif "mikrotik" in os_type:
                os_styled.stylize("bold green")

            table.add_row(dev_id, name, host, os_styled, port, user, key=dev_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-back-from-inventory", "btn-inv-home"):
            self.post_message(self.ReturnHomeRequested())
        elif event.button.id == "btn-inv-add":
            self.post_message(self.AddDeviceRequested())
        elif event.button.id == "btn-inv-refresh":
            self.reload_devices()
        elif event.button.id == "btn-inv-delete":
            table = self.query_one("#inventory-data-table", DataTable)
            if table.row_count > 0:
                coordinate = table.cursor_coordinate or (0, 0)
                try:
                    row_key = table.coordinate_to_cell_key(coordinate).row_key.value
                    dev_id = int(row_key)
                    db.delete_device(dev_id)
                    self.reload_devices()
                    self.post_message(self.DeviceDeleted())
                except Exception:
                    pass
