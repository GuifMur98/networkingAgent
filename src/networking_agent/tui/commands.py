"""Command palette provider and enterprise operations catalog for NetworkingAgent."""

from typing import List, NamedTuple

from textual.command import DiscoveryHit, Hit, Hits, Provider


class PaletteCommand(NamedTuple):
    name: str
    help_text: str
    action_name: str
    keywords: str = ""


class NetworkAgentCommandProvider(Provider):
    """Command palette provider exposing system-level and navigation operations.

    Strictly complies with enterprise mission-control styling:
    no emojis, no decorative icons, clean technical labels.
    Unifies all operational actions into four distinct categories:
    - Sistema: Configuracion global, boveda, guardarrailes, catalogo, plantillas, temas y salida.
    - Navegar: Desplazamiento rapido a cualquier modulo del sistema.
    - Consola: Limpieza de pantalla, exportacion y purga de registros de telemetria.
    - Terminal: Capturas de pantalla vectoriales, recarga/sincronizacion y atajos de teclado.
    """

    COMMANDS: List[PaletteCommand] = [
        # =========================================================================
        # 1. SISTEMA: Configuracion Global, Boveda, Guardarrailes, Temas y Sesion
        # =========================================================================
        PaletteCommand(
            "Sistema: Configurar IA y Boveda Criptografica",
            "Configura proveedor de IA (Ollama / Gemini / APIs) y almacena claves en la boveda.",
            "open_settings",
            "sistema ajustes ia boveda vault ollama gemini api key modelo cerebro configuracion",
        ),
        PaletteCommand(
            "Sistema: Alternar Modo Guardarrailes (HITL / Auto-Aprobacion)",
            "Alterna entre validacion humana obligatoria y aprobacion automatica de cambios.",
            "toggle_hitl",
            "sistema hitl auto approve human in the loop guardarrailes seguridad modo toggle",
        ),
        PaletteCommand(
            "Sistema: Registrar Nuevo Dispositivo en Catalogo",
            "Abre el formulario para anadir un equipo con credenciales seguras a la boveda.",
            "add_device",
            "sistema nuevo equipo registrar agregar dispositivo host ssh ip alta",
        ),
        PaletteCommand(
            "Sistema: Crear Nueva Plantilla de Automatizacion",
            "Abre el asistente para redactar una plantilla Jinja2 con variables dinamicas.",
            "new_template",
            "sistema nueva plantilla crear jinja2 wizard formulario template script",
        ),
        PaletteCommand(
            "Sistema: Cambiar Tema Visual de la Interfaz...",
            "Explora y aplica temas visuales (Agent Light, Agent Dark, Dracula, Nord, Tokyo Night, Gruvbox, etc.).",
            "change_theme",
            "sistema tema temas color apariencia aspecto visual dracula nord tokyo gruvbox claro oscuro light dark",
        ),
        PaletteCommand(
            "Sistema: Salir de NetworkingAgent (q)",
            "Cierra la aplicacion y desconecta de forma segura todas las sesiones SSH.",
            "quit",
            "sistema salir cerrar quit exit cerrar sesion terminate",
        ),
        # =========================================================================
        # 2. NAVEGAR: Desplazamiento a Modulos y Espacios de Trabajo
        # =========================================================================
        PaletteCommand(
            "Navegar: Inicio (Dashboard Principal)",
            "Ir a la vista general con estado de red, KPIs y accesos rapidos.",
            "go_home",
            "navegar inicio dashboard home kpi metricas panel general vista",
        ),
        PaletteCommand(
            "Navegar: Modulo 1 - Diagnostico y Troubleshooting",
            "Espacio de trabajo para analisis reactivo y proactivo asistido por IA.",
            "nav_tab_1",
            "navegar troubleshooting diagnostico fallas ai asistente reactivo proactivo modulo 1",
        ),
        PaletteCommand(
            "Navegar: Modulo 2 - Configuracion de Red",
            "Sintetizar y aplicar comandos CLI en lenguaje natural con guardarrailes.",
            "nav_tab_2",
            "navegar configuracion cli lenguaje natural aplicar rollback sintesis modulo 2",
        ),
        PaletteCommand(
            "Navegar: Modulo 3 - Automatizacion y Plantillas",
            "Gestor de plantillas Jinja2 y despliegue masivo por lotes.",
            "nav_tab_3",
            "navegar automatizacion plantillas jinja2 batch despliegue lotes scripts modulo 3",
        ),
        PaletteCommand(
            "Navegar: Modulo 4 - Inventario de Equipos",
            "Catalogo de routers, switches y firewalls con prueba de conectividad.",
            "nav_tab_4",
            "navegar inventario equipos dispositivos catalogo hardware switches routers modulo 4",
        ),
        PaletteCommand(
            "Navegar: Modulo 5 - Auditoria y Bitacora",
            "Registro forense criptografico SHA-256 inmutable de operaciones.",
            "nav_tab_5",
            "navegar auditoria bitacora sha256 forense logs inmutable registros trazabilidad modulo 5",
        ),
        PaletteCommand(
            "Navegar: Modulo 6 - Analizador de Paquetes (Captura y Diseccion)",
            "Captura y diseccion de paquetes en tiempo real con diagnostico de IA.",
            "nav_tab_6",
            "navegar analizador paquetes sniffer pcap diseccion tramas capturar doctor modulo 6",
        ),
        # =========================================================================
        # 3. CONSOLA: Telemetria, Pantalla y Registros de Ejecucion
        # =========================================================================
        PaletteCommand(
            "Consola: Limpiar Pantalla y Registros de Consola",
            "Limpia la terminal de telemetria y bitacora de salida en el espacio activo.",
            "clear_active_console",
            "consola limpiar pantalla log terminal cls clear borrar reset telemetria",
        ),
        PaletteCommand(
            "Consola: Exportar Bitacora Forense a Archivo JSON",
            "Genera un archivo JSON con todos los eventos criptograficos registrados.",
            "export_audit",
            "consola exportar auditoria json bitacora archivo respaldo descargar logs",
        ),
        PaletteCommand(
            "Consola: Purgar Registros Sinteticos de Prueba",
            "Elimina registros automaticos de test conservando los eventos reales.",
            "purge_audit_tests",
            "consola purgar limpiar borrar pruebas test registros auditoria eliminar",
        ),
        # =========================================================================
        # 4. TERMINAL: Capturas de Pantalla, Sincronizacion y Atajos de Teclado
        # =========================================================================
        PaletteCommand(
            "Terminal: Capturar Pantalla (Guardar Screenshot SVG)",
            "Guarda una captura vectorial SVG de la pantalla actual en la carpeta logs.",
            "screenshot",
            "terminal screenshot captura pantalla exportar svg imagen foto snapshot",
        ),
        PaletteCommand(
            "Terminal: Sincronizar y Recargar Todo el Sistema (F5 / r)",
            "Sincroniza bases de datos, sidebars, tablas y barra de telemetria.",
            "refresh_all",
            "terminal recargar todo refrescar sincronizar f5 r update reload actualizar",
        ),
        PaletteCommand(
            "Terminal: Ver Resumen de Atajos de Teclado",
            "Muestra una guia rapida con los accesos directos principales del sistema.",
            "show_shortcuts",
            "terminal ayuda atajos teclado teclas help shortcuts hotkeys guia",
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
