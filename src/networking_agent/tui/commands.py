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
    Focuses exclusively on system utilities, visual themes, and global navigation.
    """

    COMMANDS: List[PaletteCommand] = [
        # --- Apariencia y Temas ---
        PaletteCommand(
            "Tema: Activar Modo Claro Suave (Agent Light)",
            "Aplica la paleta clara ergonómica optimizada para descanso visual y máxima legibilidad.",
            "set_theme_agent_light",
            "claro suave light agent descanso visual blanco modo tema ergonomico",
        ),
        PaletteCommand(
            "Tema: Activar Modo Oscuro Cyberpunk (Agent Dark)",
            "Aplica la paleta oscura de centro de operaciones y ciberseguridad.",
            "set_theme_agent_dark",
            "oscuro cyberpunk dark agent control nocturno negro modo tema",
        ),
        PaletteCommand(
            "Tema: Alternar Modo Oscuro / Claro",
            "Conmuta entre la paleta de modo oscuro y modo claro del sistema.",
            "toggle_dark",
            "oscuro claro modo dark light contraste blanco negro tema",
        ),
        PaletteCommand(
            "Tema: Cambiar Tema Visual...",
            "Explora y aplica más de 20 temas visuales (Nord, Dracula, Tokyo Night, Gruvbox, etc.).",
            "change_theme",
            "tema temas color colores apariencia interfaz aspecto visual dracula nord tokyo gruvbox",
        ),
        PaletteCommand(
            "Tema: Restaurar Tema Predeterminado",
            "Restaura la apariencia original corporativa (Agent Dark).",
            "reset_theme",
            "restaurar tema default original reset reiniciar apariencia",
        ),
        # --- Navegacion a Modulos ---
        PaletteCommand(
            "Navegar: Inicio (Dashboard Principal)",
            "Ir a la vista general con estado de red, KPIs y accesos rapidos.",
            "go_home",
            "inicio dashboard home kpi metricas panel general vista",
        ),
        PaletteCommand(
            "Navegar: Modulo 1 - Diagnostico y Troubleshooting",
            "Espacio de trabajo para analisis reactivo y proactivo asistido por IA.",
            "nav_tab_1",
            "troubleshooting diagnostico fallas ai asistente reactivo proactivo modulo 1",
        ),
        PaletteCommand(
            "Navegar: Modulo 2 - Configuracion de Red",
            "Sintetizar y aplicar comandos CLI en lenguaje natural con guardarrailes.",
            "nav_tab_2",
            "configuracion cli lenguaje natural aplicar rollback sintesis modulo 2",
        ),
        PaletteCommand(
            "Navegar: Modulo 3 - Automatizacion y Plantillas",
            "Gestor de plantillas Jinja2 y despliegue masivo por lotes.",
            "nav_tab_3",
            "automatizacion plantillas jinja2 batch despliegue lotes scripts modulo 3",
        ),
        PaletteCommand(
            "Navegar: Modulo 4 - Inventario de Equipos",
            "Catalogo de routers, switches y firewalls con prueba de conectividad.",
            "nav_tab_4",
            "inventario equipos dispositivos catalogo hardware switches routers modulo 4",
        ),
        PaletteCommand(
            "Navegar: Modulo 5 - Auditoria y Bitacora",
            "Registro forense criptografico SHA-256 inmutable de operaciones.",
            "nav_tab_5",
            "auditoria bitacora sha256 forense logs inmutable registros trazabilidad modulo 5",
        ),
        # --- Configuracion y Seguridad Global ---
        PaletteCommand(
            "Sistema: Configurar IA y Boveda Criptografica",
            "Configura proveedor de IA (Ollama / Gemini / APIs) y almacena claves en la boveda.",
            "open_settings",
            "ajustes ia boveda vault ollama gemini api key modelo cerebro configuracion",
        ),
        PaletteCommand(
            "Sistema: Alternar Modo Guardarrailes (HITL / Auto-Aprobacion)",
            "Alterna entre validacion humana obligatoria y aprobacion automatica de cambios.",
            "toggle_hitl",
            "hitl auto approve human in the loop guardarrailes seguridad modo toggle",
        ),
        PaletteCommand(
            "Sistema: Registrar Nuevo Dispositivo en Catalogo",
            "Abre el formulario para anadir un equipo con credenciales seguras a la boveda.",
            "add_device",
            "nuevo equipo registrar agregar dispositivo host ssh ip alta",
        ),
        PaletteCommand(
            "Sistema: Crear Nueva Plantilla de Automatizacion",
            "Abre el asistente para redactar una plantilla Jinja2 con variables dinamicas.",
            "new_template",
            "nueva plantilla crear jinja2 wizard formulario template script",
        ),
        # --- Utilidades de Terminal ---
        PaletteCommand(
            "Consola: Limpiar Pantalla y Registros de Consola",
            "Limpia la terminal de telemetria y bitacora de salida en el espacio activo.",
            "clear_active_console",
            "limpiar consola pantalla log terminal cls clear borrar reset",
        ),
        PaletteCommand(
            "Terminal: Capturar Pantalla (Guardar Screenshot SVG)",
            "Guarda una captura vectorial SVG de la pantalla actual en la carpeta logs.",
            "screenshot",
            "screenshot captura pantalla exportar svg imagen foto snapshot",
        ),
        PaletteCommand(
            "Terminal: Sincronizar y Recargar Todo el Sistema (F5 / r)",
            "Sincroniza bases de datos, sidebars, tablas y barra de telemetria.",
            "refresh_all",
            "recargar todo refrescar sincronizar f5 r update reload actualizar",
        ),
        # --- Sesion ---
        PaletteCommand(
            "Sesion: Ver Resumen de Atajos de Teclado",
            "Muestra una guia rapida con los accesos directos principales del sistema.",
            "show_shortcuts",
            "ayuda atajos teclado teclas help shortcuts hotkeys guia",
        ),
        PaletteCommand(
            "Sesion: Salir de NetworkingAgent (q)",
            "Cierra la aplicacion y desconecta de forma segura todas las sesiones SSH.",
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
