"""Command palette provider and enterprise operations catalog for NetworkingAgent."""

from typing import List, NamedTuple

from textual.command import DiscoveryHit, Hit, Hits, Provider


class PaletteCommand(NamedTuple):
    name: str
    help_text: str
    action_name: str
    keywords: str = ""


class NetworkAgentCommandProvider(Provider):
    """Command palette provider exposing all network assistant operations.

    Strictly complies with enterprise mission-control styling:
    no emojis, no decorative icons, clean technical labels.
    """

    COMMANDS: List[PaletteCommand] = [
        # --- Navegacion a Modulos ---
        PaletteCommand(
            "Navegar: Inicio (Dashboard Principal)",
            "Ir a la vista general con estado de red, KPIs y accesos rapidos.",
            "go_home",
            "inicio dashboard home kpi metricas panel general",
        ),
        PaletteCommand(
            "Navegar: Modulo 1 - Diagnostico y Troubleshooting",
            "Espacio de trabajo para analisis reactivo y proactivo asistido por IA.",
            "nav_tab_1",
            "troubleshooting diagnostico fallas ai asistente reactivo proactivo",
        ),
        PaletteCommand(
            "Navegar: Modulo 2 - Configuracion de Red",
            "Sintetizar y aplicar comandos CLI en lenguaje natural con guardarrailes.",
            "nav_tab_2",
            "configuracion cli lenguaje natural aplicar rollback sintesis",
        ),
        PaletteCommand(
            "Navegar: Modulo 3 - Automatizacion y Plantillas",
            "Gestor de plantillas Jinja2 y despliegue masivo por lotes.",
            "nav_tab_3",
            "automatizacion plantillas jinja2 batch despliegue lotes scripts",
        ),
        PaletteCommand(
            "Navegar: Modulo 4 - Inventario de Equipos",
            "Catalogo de routers, switches y firewalls con prueba de conectividad.",
            "nav_tab_4",
            "inventario equipos dispositivos catalogo hardware switches routers ping",
        ),
        PaletteCommand(
            "Navegar: Modulo 5 - Auditoria y Bitacora",
            "Registro forense criptografico SHA-256 inmutable de operaciones.",
            "nav_tab_5",
            "auditoria bitacora sha256 forense logs inmutable registros trazabilidad",
        ),
        # --- Operaciones de Equipos y Conectividad ---
        PaletteCommand(
            "Equipos: Registrar Nuevo Dispositivo en Catalogo",
            "Abre el formulario para anadir un equipo con credenciales seguras.",
            "add_device",
            "nuevo equipo registrar agregar dispositivo host ssh ip",
        ),
        PaletteCommand(
            "Equipos: Diagnostico Completo de Conectividad (Ping + SSH)",
            "Verifica accesibilidad ICMP y estado del puerto 22 TCP (SSH).",
            "test_connectivity",
            "ping ssh conectividad probar conexion alcanzar icmp tcp 22 socket",
        ),
        PaletteCommand(
            "Equipos: Probar Ping ICMP a Dispositivo",
            "Envia paquetes ICMP Echo Request al equipo seleccionado para medir latencia.",
            "ping_device",
            "ping icmp echo latencia respuesta alcanzar prueba",
        ),
        PaletteCommand(
            "Equipos: Comprobar Puerto 22 TCP (SSH)",
            "Verifica si el servicio SSH responde conexiones TCP en el host objetivo.",
            "test_ssh_port",
            "ssh tcp puerto 22 socket conexion servicio demonio",
        ),
        PaletteCommand(
            "Equipos: Sincronizar Catalogo y Recargar Estado",
            "Recarga equipos desde la base de datos SQLite y refresca vistas.",
            "refresh_all",
            "recargar sincronizar refrescar base de datos equipos f5",
        ),
        # --- Automatizacion y Plantillas ---
        PaletteCommand(
            "Automatizacion: Crear Nueva Plantilla de Configuracion",
            "Abre el asistente para redactar una plantilla Jinja2 con variables dinamicas.",
            "new_template",
            "nueva plantilla crear jinja2 wizard formulario template",
        ),
        PaletteCommand(
            "Automatizacion: Validar Sintaxis de Script (Dry-Run)",
            "Ejecuta analisis estatico y verificacion de guardarrailes sin enviar trafico.",
            "validate_automation_script",
            "validar dry run sintaxis seguridad parseo verificacion",
        ),
        PaletteCommand(
            "Automatizacion: Seleccionar Todos los Equipos",
            "Marca todas las casillas de equipos para despliegue por lotes.",
            "select_all_automation_devices",
            "seleccionar todos marcar lista despliegue all",
        ),
        PaletteCommand(
            "Automatizacion: Deseleccionar Todos los Equipos",
            "Desmarca todas las casillas de equipos en el panel de despliegue.",
            "deselect_all_automation_devices",
            "deseleccionar desmarcar limpiar seleccion lista none",
        ),
        # --- Seguridad e Inteligencia Artificial ---
        PaletteCommand(
            "Seguridad: Alternar Modo Guardarrailes (HITL / Auto-Aprobacion)",
            "Alterna entre validacion humana obligatoria y aprobacion automatica.",
            "toggle_hitl",
            "hitl auto approve human in the loop guardarrailes seguridad modo toggle",
        ),
        PaletteCommand(
            "IA: Configurar Boveda Cifrada y Modelos de Lenguaje",
            "Configura proveedor de IA (Ollama / Gemini) y almacena claves en la boveda.",
            "open_settings",
            "ajustes ia boveda vault ollama gemini api key modelo cerebro",
        ),
        # --- Auditoria y Exportacion ---
        PaletteCommand(
            "Auditoria: Exportar Bitacora Forense a Archivo JSON",
            "Genera un archivo JSON con todos los eventos criptograficos registrados.",
            "export_audit",
            "exportar auditoria json bitacora archivo respaldo descargar",
        ),
        PaletteCommand(
            "Auditoria: Purgar Registros Sinteticos de Prueba",
            "Elimina registros automaticos de test conservando los eventos reales.",
            "purge_audit_tests",
            "purgar limpiar borrar pruebas test registros auditoria eliminar",
        ),
        # --- Diagnostico Rapido y Presets de Sintomas ---
        PaletteCommand(
            "Troubleshooting: Cargar Sintoma de Ejemplo - BGP Flapping",
            "Carga reporte de falla de sesion BGP Idle/Active en el equipo seleccionado.",
            "load_symptom_bgp",
            "bgp flapping sesion idle active peering enrutamiento ejemplo",
        ),
        PaletteCommand(
            "Troubleshooting: Cargar Sintoma de Ejemplo - Adyacencia OSPF",
            "Carga reporte de adyacencia OSPF atascada en EXSTART/EXCHANGE.",
            "load_symptom_ospf",
            "ospf adyacencia exstart exchange mtus vecindad ejemplo",
        ),
        PaletteCommand(
            "Troubleshooting: Cargar Sintoma de Ejemplo - Perdida de Paquetes",
            "Carga reporte de errores CRC y descarte de paquetes en interfaces.",
            "load_symptom_packetloss",
            "paquetes perdida crc errores interfaz caida drop ejemplo",
        ),
        PaletteCommand(
            "Troubleshooting: Cargar Sintoma de Ejemplo - Troncal VLAN",
            "Carga reporte de falla de trafico en enlaces troncales 802.1Q.",
            "load_symptom_vlan",
            "vlan troncal trunk 802.1q encapsulacion nativa ejemplo",
        ),
        PaletteCommand(
            "Consola: Limpiar Pantalla y Registros de Consola",
            "Limpia la terminal de telemetria y ejecucion en el espacio activo.",
            "clear_active_console",
            "limpiar consola pantalla log terminal cls clear borrar",
        ),
        # --- Sistema y Sesion ---
        PaletteCommand(
            "Sistema: Recargar Toda la Aplicacion (F5 / r)",
            "Sincroniza bases de datos, sidebars, tablas y barra de estado.",
            "refresh_all",
            "recargar todo refrescar sincronizar f5 r update reload",
        ),
        PaletteCommand(
            "Sistema: Ver Resumen de Atajos de Teclado",
            "Muestra una guia rapida con los accesos directos principales del sistema.",
            "show_shortcuts",
            "ayuda atajos teclado teclas help shortcuts hotkeys guia",
        ),
        PaletteCommand(
            "Sesion: Salir de NetworkingAgent (q)",
            "Cierra la aplicacion y desconecta de forma segura todas las sesiones.",
            "quit",
            "salir cerrar quit exit cerrar sesion terminate",
        ),
    ]

    async def discover(self) -> Hits:
        """Yield discovery hits shown immediately when opening the command palette."""
        for cmd in self.COMMANDS:
            callback = getattr(self.app, f"action_{cmd.action_name}", None)
            if callback is None:
                continue
            yield DiscoveryHit(
                display=cmd.name,
                command=callback,
                help=cmd.help_text,
            )

    async def search(self, query: str) -> Hits:
        """Fuzzy-search commands by title, keywords, or help text."""
        matcher = self.matcher(query)
        for cmd in self.COMMANDS:
            callback = getattr(self.app, f"action_{cmd.action_name}", None)
            if callback is None:
                continue

            score = matcher.match(cmd.name)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(cmd.name),
                    command=callback,
                    help=cmd.help_text,
                )
            else:
                # Secondary matching against keywords and help text
                kw_score = matcher.match(cmd.keywords)
                help_score = matcher.match(cmd.help_text)
                best_sec = max(kw_score, help_score)
                if best_sec > 0:
                    yield Hit(
                        score=best_sec * 0.65,
                        match_display=cmd.name,
                        command=callback,
                        help=cmd.help_text,
                    )
