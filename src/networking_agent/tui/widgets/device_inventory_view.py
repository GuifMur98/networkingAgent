"""Full device inventory management table, reachability diagnostics, and operational actions widget."""

from typing import Dict, Optional

from rich import box
from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static

from networking_agent.core.db import db
from networking_agent.engine.connectivity import ConnectivityTester
from networking_agent.models.device import DeviceInventory


class DeviceInventoryView(Widget):
    """View allowing operator to inspect, add, test connectivity, and delete registered devices."""

    class AddDeviceRequested(Message):
        """Emitted when the operator clicks the add device button."""

    class DeviceDeleted(Message):
        """Emitted when a device is deleted so the app can refresh counts."""

    class ReturnHomeRequested(Message):
        """Emitted when the operator wants to return to the Home/Inicio view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.device_cache: Dict[str, DeviceInventory] = {}
        self.device_meta: Dict[str, dict] = {}
        self.connectivity_cache: Dict[str, str] = {}
        self.status_col_key = None

    def compose(self) -> ComposeResult:
        with Vertical(id="inventory-container"):
            with Vertical(id="inventory-content-wrapper", classes="workspace-content-wrapper"):
                # 1. Header Navigation Bar
                with Horizontal(id="inventory-top-bar"):
                    yield Label(
                        "INVENTARIO DE EQUIPOS // GESTION DE INFRAESTRUCTURA Y CONECTIVIDAD",
                        id="inventory-title",
                    )
                    yield Button("Volver al Inicio (h)", id="btn-back-from-inventory")

                # 2. Operational Actions Toolbar (Sleek unified card)
                with Horizontal(id="inventory-toolbar", classes="section-panel"):
                    with Horizontal(id="inventory-crud-actions"):
                        yield Button("+ Registrar Equipo (d)", id="btn-inv-add", variant="primary")
                        yield Button("Eliminar", id="btn-inv-delete", variant="error")
                        yield Button("Recargar (r)", id="btn-inv-refresh")

                    with Horizontal(id="inventory-diagnostic-actions"):
                        yield Button("Hacer Ping (ICMP)", id="btn-inv-ping")
                        yield Button("Probar Conexión (SSH)", id="btn-inv-test-conn")
                        yield Button("Test Completo", id="btn-inv-test-all")

                # 3. Main Inventory Table with generous cell spacing
                yield DataTable(id="inventory-data-table", cursor_type="row", zebra_stripes=True)

                # 4. Live Connectivity & Telemetry Diagnostic Card
                yield Static(id="inventory-diagnostic-card")

    def on_mount(self) -> None:
        table = self.query_one("#inventory-data-table", DataTable)
        table.cell_padding = 2
        cols = table.add_columns(
            "ID",
            "Nombre / Alias",
            "Host / IP",
            "Sistema Operativo",
            "Puerto",
            "Usuario SSH",
            "Estado Conectividad",
        )
        self.status_col_key = cols[-1]
        self.reload_devices()
        self._reset_diagnostic_panel()

    def _get_theme_palette(self):
        theme = getattr(self.app, "current_theme", None)
        is_dark = getattr(theme, "dark", True) if theme else True
        return {
            "is_dark": is_dark,
            "primary": "#00e5ff" if is_dark else "#0369a1",
            "secondary": "#00b4d8" if is_dark else "#475569",
            "border": "#00b4d8" if is_dark else "#cbd5e1",
            "success": "#4ade80" if is_dark else "#16a34a",
            "warning": "#fbbf24" if is_dark else "#d97706",
            "error": "#f43f5e" if is_dark else "#dc2626",
            "fg": "#e2e8f0" if is_dark else "#1e293b",
            "cyan": "cyan" if is_dark else "#0284c7",
        }

    def _reset_diagnostic_panel(self) -> None:
        diag = self.query_one("#inventory-diagnostic-card", Static)
        pal = self._get_theme_palette()
        msg = (
            f"[{pal['cyan']}]Selecciona un equipo de la tabla y pulsa [bold]Hacer Ping (ICMP)[/bold], "
            "[bold]Probar Conexión (SSH)[/bold] o [bold]Test Completo[/bold] para verificar la alcanzabilidad "
            f"y latencia de red en tiempo real.[/{pal['cyan']}]"
        )
        diag.update(
            Panel(
                msg,
                title="DIAGNOSTICO DE CONECTIVIDAD Y ALCANZABILIDAD EN VIVO",
                border_style=pal["border"],
                box=box.ROUNDED,
            )
        )

    def reload_devices(self) -> None:
        """Refreshes the DataTable with enrolled devices from SQLite database."""
        table = self.query_one("#inventory-data-table", DataTable)
        table.clear()
        self.device_cache.clear()
        self.device_meta.clear()
        devices = db.list_devices()

        for dev in devices:
            dev_id = str(dev.get("id", ""))
            name = dev.get("name", "")
            host = dev.get("host", "")
            os_type = dev.get("device_type", "")
            port = str(dev.get("port", 22))
            user = dev.get("username", "")

            self.device_meta[dev_id] = dev

            # Cache hydrated device
            hydrated = db.get_device_by_id(int(dev_id))
            if hydrated:
                self.device_cache[dev_id] = hydrated

            # Styled Operating System column
            os_styled = Text(os_type)
            if "cisco" in os_type:
                os_styled.stylize("bold bright_blue")
            elif "juniper" in os_type:
                os_styled.stylize("bold magenta")
            elif "mikrotik" in os_type:
                os_styled.stylize("bold green")

            # Status cell
            status = self.connectivity_cache.get(dev_id, "[dim]Sin Verificar[/dim]")
            table.add_row(
                dev_id,
                name,
                Text(host, style="bold cyan"),
                os_styled,
                port,
                user,
                Text.from_markup(status),
                key=dev_id,
            )

    def _get_selected_device_entry(self) -> Optional[tuple[str, str, DeviceInventory]]:
        """Resolves (dev_id, dev_name, device) from the highlighted DataTable row."""
        table = self.query_one("#inventory-data-table", DataTable)
        if table.row_count == 0 or not self.device_cache:
            return None
        coord = table.cursor_coordinate or (0, 0)
        try:
            row_key = str(table.coordinate_to_cell_key(coord).row_key.value)
        except Exception:
            row_key = next(iter(self.device_cache.keys()))

        device = self.device_cache.get(row_key)
        if not device:
            if self.device_cache:
                row_key = next(iter(self.device_cache.keys()))
                device = self.device_cache[row_key]
            else:
                return None

        dev_name = self.device_meta.get(row_key, {}).get("name") or device.host
        return row_key, dev_name, device

    def _update_device_status_in_table(self, dev_id: str, status_markup: str) -> None:
        """Updates the connectivity status column for the given device."""
        self.connectivity_cache[dev_id] = status_markup
        table = self.query_one("#inventory-data-table", DataTable)
        try:
            if self.status_col_key is not None:
                table.update_cell(row_key=dev_id, column_key=self.status_col_key, value=Text.from_markup(status_markup))
            else:
                self.reload_devices()
        except Exception:
            self.reload_devices()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("btn-back-from-inventory", "btn-inv-home"):
            self.post_message(self.ReturnHomeRequested())
        elif btn_id == "btn-inv-add":
            self.post_message(self.AddDeviceRequested())
        elif btn_id == "btn-inv-refresh":
            self.reload_devices()
            self._reset_diagnostic_panel()
        elif btn_id == "btn-inv-delete":
            self._delete_selected_device()
        elif btn_id == "btn-inv-ping":
            self.action_ping_device()
        elif btn_id == "btn-inv-test-conn":
            self.action_test_connection()
        elif btn_id == "btn-inv-test-all":
            self.action_test_full_connectivity()

    def _delete_selected_device(self) -> None:
        """Deletes the highlighted device from SQLite storage."""
        table = self.query_one("#inventory-data-table", DataTable)
        if table.row_count > 0:
            coord = table.cursor_coordinate or (0, 0)
            try:
                row_key = table.coordinate_to_cell_key(coord).row_key.value
                dev_id = int(row_key)
                db.delete_device(dev_id)
                self.reload_devices()
                self.post_message(self.DeviceDeleted())
                diag = self.query_one("#inventory-diagnostic-card", Static)
                diag.update(
                    Panel(
                        f"[yellow]Equipo ID {dev_id} eliminado exitosamente del catálogo.[/yellow]",
                        title="REGISTRO ACTUALIZADO",
                        border_style="#fbbf24",
                        box=box.ROUNDED,
                    )
                )
            except Exception:
                pass

    @work(exclusive=True)
    async def action_ping_device(self) -> None:
        """Executes ICMP echo request probe against the selected device."""
        selected = self._get_selected_device_entry()
        diag = self.query_one("#inventory-diagnostic-card", Static)
        if not selected:
            diag.update(
                Panel(
                    "[yellow]Aviso: No hay ningún equipo seleccionado en la tabla para hacer ping.[/yellow]",
                    title="TEST ICMP CANCELADO",
                    border_style="#fbbf24",
                    box=box.ROUNDED,
                )
            )
            return

        dev_id, dev_name, device = selected
        diag.update(
            Panel(
                f"[bold cyan]Enviando paquetes ICMP Echo Request a {device.host} ({dev_name})...[/bold cyan]",
                title=f"TEST ICMP // {device.host}",
                border_style="#00b4d8",
                box=box.ROUNDED,
            )
        )

        result = await ConnectivityTester.ping(device.host, count=2)

        if result.is_reachable:
            content = (
                f"[bold green][OK] PING ICMP: ALCANZABLE[/bold green]\n\n"
                f"  * Host destino: [bold white]{device.host}[/bold white] ({dev_name})\n"
                f"  * Latencia RTT promedio: [bold cyan]{result.rtt_avg}[/bold cyan]\n"
                f"  * Paquetes de red: {result.sent} transmitidos, {result.received} recibidos "
                f"([bold green]{result.packet_loss} pérdida[/bold green])\n"
                f"  * Estado Capa 3: Enlace operacional y respondiendo a tramas de red"
            )
            panel = Panel(
                content,
                title=f"TEST ICMP EXITOSO // {device.host}",
                border_style="#4ade80",
                box=box.ROUNDED,
            )
            self._update_device_status_in_table(dev_id, f"[bold green]En Línea ({result.rtt_avg})[/bold green]")
        else:
            content = (
                f"[bold red][!] PING ICMP: INALCANZABLE[/bold red]\n\n"
                f"  * Host destino: [bold white]{device.host}[/bold white] ({dev_name})\n"
                f"  * Paquetes de red: {result.sent} transmitidos, 0 recibidos "
                f"([bold red]{result.packet_loss} pérdida[/bold red])\n"
                f"  * Diagnóstico L3: El equipo no responde a tramas de eco ICMP.\n\n"
                f"[dim yellow]Aviso: Verifique que la IP sea correcta, el equipo esté encendido y que las ACLs "
                f"o firewall permitan tráfico ICMP.[/dim yellow]"
            )
            panel = Panel(
                content,
                title=f"TEST ICMP FALLIDO // {device.host}",
                border_style="#f43f5e",
                box=box.ROUNDED,
            )
            self._update_device_status_in_table(dev_id, "[bold red]Inalcanzable[/bold red]")

        diag.update(panel)

    @work(exclusive=True)
    async def action_test_connection(self) -> None:
        """Executes TCP socket probe to verify port listening state."""
        selected = self._get_selected_device_entry()
        diag = self.query_one("#inventory-diagnostic-card", Static)
        if not selected:
            diag.update(
                Panel(
                    "[yellow]Aviso: No hay ningún equipo seleccionado en la tabla para probar conexión.[/yellow]",
                    title="PROBA DE CONEXION CANCELADA",
                    border_style="#fbbf24",
                    box=box.ROUNDED,
                )
            )
            return

        dev_id, dev_name, device = selected
        pal = self._get_theme_palette()
        diag.update(
            Panel(
                f"[bold {pal['cyan']}]Verificando socket TCP en {device.host}:{device.port}...[/bold {pal['cyan']}]",
                title=f"TEST PUERTO SSH // {device.host}:{device.port}",
                border_style=pal["border"],
                box=box.ROUNDED,
            )
        )

        result = await ConnectivityTester.check_port(device.host, device.port)

        if result.is_open:
            content = (
                f"[bold green][OK] PUERTO TCP {device.port}: ABIERTO[/bold green]\n\n"
                f"  * Host destino: [bold white]{device.host}:{device.port}[/bold white] ({dev_name})\n"
                f"  * Plataforma esperada: [bold white]{device.device_type}[/bold white]\n"
                f"  * Tiempo de establecimiento TCP: [bold cyan]{result.elapsed_ms}ms[/bold cyan]\n"
                f"  * Estado Capa 4: El demonio SSH está escuchando y aceptando sesiones entrantes"
            )
            panel = Panel(
                content,
                title=f"PUERTO SSH ABIERTO // {device.host}:{device.port}",
                border_style="#4ade80",
                box=box.ROUNDED,
            )
            self._update_device_status_in_table(dev_id, f"[bold green]SSH Abierto ({result.elapsed_ms}ms)[/bold green]")
        else:
            err_msg = result.error or "Conexión rechazada o timeout"
            notice = (
                f"[dim yellow]Aviso: El servicio SSH no está activo en el puerto {device.port} o una lista de "
                f"acceso (ACL) está descartando los paquetes TCP SYN.[/dim yellow]"
            )
            content = (
                f"[bold red][!] PUERTO TCP {device.port}: CERRADO O BLOQUEADO[/bold red]\n\n"
                f"  * Host destino: [bold white]{device.host}:{device.port}[/bold white] ({dev_name})\n"
                f"  * Detalle de error: [bold red]{err_msg}[/bold red]\n\n"
                f"{notice}"
            )
            panel = Panel(
                content,
                title=f"PUERTO SSH CERRADO // {device.host}:{device.port}",
                border_style="#f43f5e",
                box=box.ROUNDED,
            )
            self._update_device_status_in_table(dev_id, "[bold red]Puerto Cerrado[/bold red]")

        diag.update(panel)

    @work(exclusive=True)
    async def action_test_full_connectivity(self) -> None:
        """Executes multi-tier reachability inspection: Ping + TCP Port."""
        selected = self._get_selected_device_entry()
        diag = self.query_one("#inventory-diagnostic-card", Static)
        if not selected:
            diag.update(
                Panel(
                    "[yellow]Aviso: No hay ningún equipo seleccionado en la tabla.[/yellow]",
                    title="TEST INTEGRAL CANCELADO",
                    border_style="#fbbf24",
                    box=box.ROUNDED,
                )
            )
            return

        dev_id, dev_name, device = selected
        pal = self._get_theme_palette()
        diag.update(
            Panel(
                f"[bold {pal['cyan']}]Ejecutando diagnóstico multi-capa (ICMP + TCP) en "
                f"{device.host}...[/bold {pal['cyan']}]",
                title=f"TEST MULTI-TIER // {device.host}",
                border_style=pal["border"],
                box=box.ROUNDED,
            )
        )

        ping_res = await ConnectivityTester.ping(device.host)
        port_res = await ConnectivityTester.check_port(device.host, device.port)

        ping_status = (
            f"[bold green]ALCANZABLE (RTT {ping_res.rtt_avg})[/bold green]"
            if ping_res.is_reachable
            else f"[bold red]FALLIDO ({ping_res.packet_loss} pérdida)[/bold red]"
        )

        port_status = (
            f"[bold green]ABIERTO ({port_res.elapsed_ms}ms)[/bold green]"
            if port_res.is_open
            else f"[bold red]CERRADO ({port_res.error or 'Timeout'})[/bold red]"
        )

        is_healthy = ping_res.is_reachable and port_res.is_open
        if is_healthy:
            border_col = "#4ade80"
            overall_msg = (
                "[bold green]Estado General: El equipo se encuentra completamente operativo "
                "y listo para gestión remota.[/bold green]"
            )
            table_status = f"[bold green]Operativo ({ping_res.rtt_avg})[/bold green]"
        elif ping_res.is_reachable or port_res.is_open:
            border_col = "#fbbf24"
            overall_msg = (
                "[bold yellow]Estado General: Alcanzable parcialmente. "
                "Verifique los servicios que no respondieron.[/bold yellow]"
            )
            table_status = "[bold yellow]Parcial[/bold yellow]"
        else:
            border_col = "#f43f5e"
            overall_msg = (
                "[bold red]Estado General: Equipo inalcanzable. Verifique alimentación y enlace físico.[/bold red]"
            )
            table_status = "[bold red]Inalcanzable[/bold red]"

        content = (
            f"─── DIAGNOSTICO INTEGRAL DE EQUIPO: [bold white]{device.host}[/bold white] ({dev_name}) ───\n\n"
            f"  * Capa 3 (ICMP Echo): {ping_status}\n"
            f"  * Capa 4 (TCP Puerto {device.port}): {port_status}\n"
            f"  * Sistema Operativo: [bold cyan]{device.device_type}[/bold cyan]\n"
            f"  * Usuario Configurado: [bold white]{device.username}[/bold white]\n\n"
            f"{overall_msg}"
        )

        panel = Panel(
            content,
            title=f"REPORTE DE SALUD // {device.host}",
            border_style=border_col,
            box=box.ROUNDED,
        )

        self._update_device_status_in_table(dev_id, table_status)
        diag.update(panel)
