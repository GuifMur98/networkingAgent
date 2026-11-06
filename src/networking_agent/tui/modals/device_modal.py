"""Modal screen for registering network devices into encrypted SQLite storage."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from networking_agent.core.db import db
from networking_agent.models.device import DeviceInventory


class DeviceModal(ModalScreen[Optional[DeviceInventory]]):
    """Dialog screen for securely enrolling a new network device."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    OS_CHOICES = [
        ("Cisco IOS / IOS-XE", "cisco_ios"),
        ("Cisco NX-OS", "cisco_nxos"),
        ("Juniper Junos", "juniper_junos"),
        ("MikroTik RouterOS", "mikrotik_routeros"),
        ("Linux Generic", "linux"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-screen"):
            with Vertical(classes="modal-dialog"):
                yield Label("REGISTRO DE NUEVO EQUIPO DE RED", classes="modal-title")

                yield Label("Dirección IP o Nombre de Host (FQDN):")
                yield Input(placeholder="Ej: 192.168.1.1 o switch-core01", id="input-host")

                yield Label("Sistema Operativo de Red:")
                yield Select(self.OS_CHOICES, value="cisco_ios", id="select-os", allow_blank=False)

                yield Label("Puerto SSH:")
                yield Input(value="22", id="input-port")

                yield Label("Nombre de Usuario SSH:")
                yield Input(value="admin", id="input-username")

                yield Label("Contraseña SSH:")
                yield Input(placeholder="Contraseña del equipo", password=True, id="input-password")

                yield Label("Secret / Contraseña Enable (Opcional):")
                yield Input(placeholder="Secret enable para Cisco", password=True, id="input-secret")

                yield Label("", id="lbl-error", classes="error-label")

                with Horizontal(classes="modal-actions"):
                    yield Button("Guardar Equipo", id="btn-save-device", variant="success")
                    yield Button("Cancelar", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-device":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        host = self.query_one("#input-host", Input).value.strip()
        os_select = self.query_one("#select-os", Select)
        device_type = str(os_select.value)
        port_raw = self.query_one("#input-port", Input).value.strip()
        username = self.query_one("#input-username", Input).value.strip()
        password = self.query_one("#input-password", Input).value
        secret = self.query_one("#input-secret", Input).value

        error_label = self.query_one("#lbl-error", Label)

        try:
            port = int(port_raw)
            device = DeviceInventory(
                host=host,
                device_type=device_type,
                port=port,
                username=username,
                password=password,
                secret=secret or None,
            )
            # Save to SQLite with AES-128 Fernet encryption
            db.save_device(device)
            self.dismiss(device)
        except Exception as e:
            error_label.update(f"[bold red]Error: {e}[/bold red]")

    def action_cancel(self) -> None:
        self.dismiss(None)
