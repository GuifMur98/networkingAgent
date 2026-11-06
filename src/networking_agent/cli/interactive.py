"""Interactive configuration and onboarding wizard for NetworkingAgent with SQLite persistence."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import SecretStr
from rich.table import Table

from networking_agent.cli.prompts import (
    prompt_choice,
    prompt_confirm,
    prompt_int_range,
    prompt_non_empty,
)
from networking_agent.cli.ui_theme import print_step_header
from networking_agent.core.config import settings
from networking_agent.core.db import db
from networking_agent.core.logging import console, logger
from networking_agent.models.device import DeviceInventory


def discover_ollama_models(host: Optional[str] = None) -> List[Dict[str, Any]]:
    """Connects to local Ollama and discovers installed models."""
    ollama_url = host or settings.ollama_host
    try:
        from ollama import Client

        client = Client(host=ollama_url)
        response = client.list()
        discovered = []
        for m in response.models:
            model_name = getattr(m, "model", None) or getattr(m, "name", str(m))
            size_bytes = getattr(m, "size", 0)
            size_gb = f"{size_bytes / (1024**3):.1f} GB" if size_bytes else "N/A"
            discovered.append({"name": model_name, "size": size_gb})
        return discovered
    except Exception as e:
        logger.debug(f"Could not connect to Ollama at {ollama_url}: {e}")
        return []


def select_ai_brain_interactively(
    default_provider: Optional[str] = None,
    default_model: Optional[str] = None,
) -> Tuple[str, str]:
    """Prompts the user interactively to select the AI Brain provider and model."""
    print_step_header(
        step=1,
        total=3,
        title="🧠 Selección del Cerebro de Inteligencia Artificial",
        subtitle="Elige el motor de inferencia encargado de diagnosticar y diseñar la remediación neutral.",
    )

    saved_provider = db.get_setting("ai_provider")
    saved_model = db.get_setting("ai_model")

    # 1. Selection of AI Provider
    providers = [
        ("ollama", "Ollama (Inferencia 100% Local y Privada en tu propia máquina)"),
        ("gemini", "Google Gemini (Gemini 3.8 Flash / 4 Argon vía Cloud API)"),
        ("openai", "OpenAI (GPT-4o / GPT-4o-mini vía Cloud API)"),
        ("anthropic", "Anthropic (Claude 3.5 Sonnet vía Cloud API)"),
    ]

    provider_table = Table(show_header=True, header_style="bold magenta")
    provider_table.add_column("Opción", style="bold yellow", width=8, justify="center")
    provider_table.add_column("Proveedor", style="bold", width=14)
    provider_table.add_column("Descripción")

    for idx, (p_id, p_desc) in enumerate(providers, 1):
        provider_table.add_row(str(idx), p_id, p_desc)
    console.print(provider_table)

    initial_choice = default_provider or saved_provider or "1"
    default_idx = "1"
    for idx, (p_id, _) in enumerate(providers, 1):
        if p_id == initial_choice or str(idx) == initial_choice:
            default_idx = str(idx)
            break

    prov_choice = prompt_choice(
        "Selecciona el proveedor de IA [1-4]",
        choices=["1", "2", "3", "4"],
        default=default_idx,
    )
    selected_provider = providers[int(prov_choice) - 1][0]

    # 2. Model selection for Ollama
    if selected_provider == "ollama":
        installed_models = discover_ollama_models()
        if installed_models:
            console.print("\n[bold green]Modelos detectados en tu servidor local de Ollama:[/bold green]")
            model_table = Table(show_header=True, header_style="bold cyan")
            model_table.add_column("Opción", style="bold yellow", width=8, justify="center")
            model_table.add_column("Nombre del Modelo", style="bold")
            model_table.add_column("Tamaño", style="dim", width=12)

            for idx, m in enumerate(installed_models, 1):
                star = " 🌟 (Recomendado para Redes)" if "netexpert" in m["name"].lower() else ""
                model_table.add_row(str(idx), f"{m['name']}{star}", m["size"])
            console.print(model_table)

            choices = [str(i) for i in range(1, len(installed_models) + 1)]
            choices.append("c")  # Custom

            # Determine best default choice
            model_default_idx = "1"
            if saved_model:
                for idx, m in enumerate(installed_models, 1):
                    if m["name"] == saved_model:
                        model_default_idx = str(idx)
                        break
            else:
                for idx, m in enumerate(installed_models, 1):
                    if "netexpert" in m["name"].lower():
                        model_default_idx = str(idx)
                        break

            picked = prompt_choice(
                f"Selecciona el modelo a usar [1-{len(installed_models)}] o 'c' para ingresar otro",
                choices=choices,
                default=model_default_idx,
            )

            if picked == "c":
                selected_model = prompt_non_empty("Ingresa el nombre exacto del modelo en Ollama")
            else:
                selected_model = installed_models[int(picked) - 1]["name"]
        else:
            console.print("[yellow]No se detectaron modelos activos en Ollama o el servicio no respondió.[/yellow]")
            selected_model = prompt_non_empty(
                "Ingresa el nombre del modelo de Ollama a utilizar",
                default=saved_model or "llama3.1",
            )

    # 3. Model selection for Google Gemini
    elif selected_provider == "gemini":
        gemini_key = db.get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            console.print("[dim]✓ API Key de Gemini recuperada desde almacén seguro SQLite.[/dim]")
            if prompt_confirm("¿Deseas actualizar la GEMINI_API_KEY almacenada?", default=False):
                gemini_key = prompt_non_empty("Ingresa tu nueva GEMINI_API_KEY", password=True)
                db.set_setting("gemini_api_key", gemini_key, is_secret=True)
        else:
            gemini_key = prompt_non_empty("Ingresa tu GEMINI_API_KEY", password=True)
            if prompt_confirm("¿Deseas almacenar esta API Key de forma cifrada en la base de datos?", default=True):
                db.set_setting("gemini_api_key", gemini_key, is_secret=True)

        os.environ["GEMINI_API_KEY"] = gemini_key

        console.print("\n[bold]Modelos de Google Gemini disponibles:[/bold]")
        gemini_models = [
            "gemini-3.8-flash",
            "gemini-4-argon",
            "gemini-3.5-flash-lite",
            "Personalizado",
        ]
        for idx, m in enumerate(gemini_models, 1):
            star = " 🌟 (Recomendado: Rápido y Equilibrado)" if m == "gemini-3.8-flash" else ""
            console.print(f"  [yellow]{idx}[/yellow]. {m}{star}")
        m_idx = prompt_choice("Selecciona modelo", choices=["1", "2", "3", "4"], default="1")
        if m_idx == "4":
            selected_model = prompt_non_empty("Ingresa el identificador del modelo (ej. gemini-3.8-flash)")
        else:
            selected_model = gemini_models[int(m_idx) - 1]

    # 4. Model selection for OpenAI
    elif selected_provider == "openai":
        openai_key = db.get_setting("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        if openai_key:
            console.print("[dim]✓ API Key de OpenAI recuperada desde almacén seguro SQLite.[/dim]")
            if prompt_confirm("¿Deseas actualizar la OPENAI_API_KEY almacenada?", default=False):
                openai_key = prompt_non_empty("Ingresa tu nueva OPENAI_API_KEY", password=True)
                db.set_setting("openai_api_key", openai_key, is_secret=True)
        else:
            openai_key = prompt_non_empty("Ingresa tu OPENAI_API_KEY", password=True)
            if prompt_confirm("¿Deseas almacenar esta API Key de forma cifrada en la base de datos?", default=True):
                db.set_setting("openai_api_key", openai_key, is_secret=True)

        os.environ["OPENAI_API_KEY"] = openai_key

        console.print("\n[bold]Modelos de OpenAI disponibles:[/bold]")
        openai_models = ["gpt-4o", "gpt-4o-mini", "o1-mini", "Personalizado"]
        for idx, m in enumerate(openai_models, 1):
            console.print(f"  [yellow]{idx}[/yellow]. {m}")
        m_idx = prompt_choice("Selecciona modelo", choices=["1", "2", "3", "4"], default="1")
        if m_idx == "4":
            selected_model = prompt_non_empty("Ingresa el identificador del modelo")
        else:
            selected_model = openai_models[int(m_idx) - 1]

    # 5. Model selection for Anthropic
    else:
        anthropic_key = db.get_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            console.print("[dim]✓ API Key de Anthropic recuperada desde almacén seguro SQLite.[/dim]")
            if prompt_confirm("¿Deseas actualizar la ANTHROPIC_API_KEY almacenada?", default=False):
                anthropic_key = prompt_non_empty("Ingresa tu nueva ANTHROPIC_API_KEY", password=True)
                db.set_setting("anthropic_api_key", anthropic_key, is_secret=True)
        else:
            anthropic_key = prompt_non_empty("Ingresa tu ANTHROPIC_API_KEY", password=True)
            if prompt_confirm("¿Deseas almacenar esta API Key de forma cifrada en la base de datos?", default=True):
                db.set_setting("anthropic_api_key", anthropic_key, is_secret=True)

        os.environ["ANTHROPIC_API_KEY"] = anthropic_key

        console.print("\n[bold]Modelos de Anthropic disponibles:[/bold]")
        anthropic_models = [
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "Personalizado",
        ]
        for idx, m in enumerate(anthropic_models, 1):
            console.print(f"  [yellow]{idx}[/yellow]. {m}")
        m_idx = prompt_choice("Selecciona modelo", choices=["1", "2", "3"], default="1")
        if m_idx == "3":
            selected_model = prompt_non_empty("Ingresa el identificador del modelo")
        else:
            selected_model = anthropic_models[int(m_idx) - 1]

    # Remember preferred provider and model in database
    db.set_setting("ai_provider", selected_provider)
    db.set_setting("ai_model", selected_model)

    console.print(
        f"\n[bold green]✓ Cerebro configurado y guardado:[/bold green] "
        f"[bold]{selected_provider.upper()} / {selected_model}[/bold]\n"
    )
    return selected_provider, selected_model


def configure_device_interactively(
    default_host: Optional[str] = None,
    default_type: Optional[str] = None,
) -> DeviceInventory:
    """Prompts the user interactively to configure target device credentials or choose from SQLite vault."""
    print_step_header(
        step=2,
        total=3,
        title="🔌 Configuración de Conexión al Dispositivo de Red",
        subtitle="Selecciona un equipo guardado en la base de datos o da de alta un nuevo dispositivo SSH.",
    )

    # 1. Check if there are saved devices in SQLite
    saved_devices = db.list_devices()
    if saved_devices:
        console.print("[bold green]💾 Equipos guardados en la base de datos SQLite:[/bold green]")
        saved_table = Table(show_header=True, header_style="bold cyan")
        saved_table.add_column("Opción", style="bold yellow", width=8, justify="center")
        saved_table.add_column("Perfil / Nombre", style="bold")
        saved_table.add_column("Host / IP", style="cyan")
        saved_table.add_column("Plataforma", style="dim")
        saved_table.add_column("Usuario", style="white")

        for idx, dev_row in enumerate(saved_devices, 1):
            saved_table.add_row(
                str(idx),
                dev_row["name"],
                dev_row["host"],
                dev_row["device_type"],
                dev_row["username"],
            )
        console.print(saved_table)

        choices = [str(i) for i in range(1, len(saved_devices) + 1)]
        choices.append("n")  # New device

        pick = prompt_choice(
            f"Selecciona un equipo guardado [1-{len(saved_devices)}] o 'n' para configurar uno nuevo",
            choices=choices,
            default="1",
        )

        if pick != "n":
            chosen_dev_id = saved_devices[int(pick) - 1]["id"]
            loaded_device = db.get_device_by_id(chosen_dev_id)
            if loaded_device:
                console.print(
                    f"\n[green]✓ Equipo cargado desde la base de datos:[/green] "
                    f"[bold]{loaded_device.host}[/bold] ([cyan]{loaded_device.device_type}[/cyan]) "
                    f"con usuario [bold]{loaded_device.username}[/bold]\n"
                )
                return loaded_device

    # 2. Configure a New Device
    console.print("\n[bold cyan]Configuración de Nuevo Dispositivo:[/bold cyan]")
    host = prompt_non_empty(
        "Dirección IP o FQDN del dispositivo",
        default=default_host or os.environ.get("NET_HOST", "10.10.20.11"),
    )

    platforms = [
        ("cisco_nxos", "Cisco Nexus (NX-OS) con soporte transaccional y checkpoints"),
        ("cisco_ios", "Cisco IOS clásico o IOS-XE (Catalyst, ISR, ASR)"),
        ("cisco_xr", "Cisco IOS-XR Carrier-Grade con commit confirmed"),
        ("juniper_junos", "Juniper Junos OS con commit confirmed"),
        ("mikrotik_routeros", "MikroTik RouterOS (v6/v7) con export y backups"),
    ]

    plat_table = Table(show_header=True, header_style="bold magenta")
    plat_table.add_column("Opción", style="bold yellow", width=8, justify="center")
    plat_table.add_column("Plataforma", style="bold", width=18)
    plat_table.add_column("Descripción")

    for idx, (p_id, p_desc) in enumerate(platforms, 1):
        plat_table.add_row(str(idx), p_id, p_desc)
    console.print(plat_table)

    plat_choice = prompt_choice(
        "Selecciona el Sistema Operativo del equipo [1-5]",
        choices=["1", "2", "3", "4", "5"],
        default="1"
        if not default_type
        else str(
            [p[0] for p in platforms].index(default_type) + 1 if default_type in [p[0] for p in platforms] else "1"
        ),
    )
    selected_platform = platforms[int(plat_choice) - 1][0]

    port = prompt_int_range("Puerto SSH", min_val=1, max_val=65535, default=22)
    username = prompt_non_empty("Usuario SSH", default=os.environ.get("NET_USER", "admin"))
    auth_type = prompt_choice("Tipo de autenticación SSH", choices=["password", "key"], default="password")

    password: Optional[SecretStr] = None
    secret: Optional[SecretStr] = None
    key_file: Optional[str] = None
    use_keys = False

    if auth_type == "password":
        existing_pass = os.environ.get("NET_PASS")
        if existing_pass:
            use_existing = prompt_confirm(
                "¿Deseas usar la contraseña definida en la variable de entorno NET_PASS?",
                default=True,
            )
            if use_existing:
                password = SecretStr(existing_pass)

        if not password:
            raw_pass = prompt_non_empty("Ingresa la contraseña SSH del equipo", password=True)
            password = SecretStr(raw_pass) if raw_pass else None

        has_enable = prompt_confirm(
            "¿El equipo requiere contraseña de modo privilegiado (enable secret)?",
            default=False,
        )
        if has_enable:
            raw_secret = prompt_non_empty("Ingresa el enable secret", password=True)
            secret = SecretStr(raw_secret) if raw_secret else None
    else:
        use_keys = True
        key_file = prompt_non_empty(
            "Ruta a la llave privada SSH",
            default=str(Path.home() / ".ssh" / "id_rsa"),
        )

    device = DeviceInventory(
        host=host,
        device_type=selected_platform,  # type: ignore
        username=username,
        password=password,
        secret=secret,
        port=port,
        key_file=key_file,
        use_keys=use_keys,
    )

    # Offer to save in SQLite vault
    if prompt_confirm("¿Deseas guardar este equipo en la base de datos local SQLite para futuros usos?", default=True):
        friendly_name = prompt_non_empty(
            "Nombre o alias para este equipo",
            default=f"{selected_platform.upper()}-{host}",
        )
        db.save_device(device, name=friendly_name)
        console.print("[dim]✓ Dispositivo guardado de forma cifrada en SQLite.[/dim]")

    console.print(
        f"\n[green]✓ Dispositivo configurado:[/green] [bold]{device.host}[/bold] "
        f"([cyan]{device.device_type}[/cyan]) con usuario [bold]{device.username}[/bold]\n"
    )
    return device


def prompt_telemetry_event() -> Tuple[str, str]:
    """Allows selecting between Proactive Symptom Investigation or Reactive Syslog Alerting."""
    print_step_header(
        step=3,
        total=3,
        title="🔍 Selección del Modo de Diagnóstico y Telemetría",
        subtitle="Elige si deseas investigar proactivamente un síntoma reportado o analizar un Syslog reactivo.",
    )

    console.print(
        "  [bold yellow]1[/bold yellow]. [bold green]Modo Proactivo / Investigación de Síntomas[/bold green] "
        "(Pérdidas de paquetes en LAN, lentitud, errores CRC, caídas)"
    )
    console.print(
        "  [bold yellow]2[/bold yellow]. [bold blue]Modo Reactivo / Análisis de Syslog[/bold blue] "
        "(Eventos críticos capturados en log del switch o router)"
    )

    mode_choice = prompt_choice("Selecciona el modo [1-2]", choices=["1", "2"], default="1")

    if mode_choice == "1":
        proactive_scenarios = [
            (
                "Pérdida de Paquetes en LAN y Caídas Intermitentes",
                (
                    "SÍNTOMA OPERACIONAL REPORTADO: Los usuarios del segmento LAN reportan un 20% a 30% "
                    "de pérdida de paquetes hacia el router y latencia anormalmente alta. "
                    "El ping hacia el gateway es intermitente. La red LAN está conectada a la interfaz ether2 "
                    "(o GigabitEthernet1/0/2)."
                ),
            ),
            (
                "Errores CRC y Descarte Masivo de Tramas (Duplex/Speed Mismatch)",
                (
                    "SÍNTOMA OPERACIONAL REPORTADO: El enlace presenta lentitud extrema y pérdida de paquetes. "
                    "La interfaz reporta colisiones tardías (late collisions), errores CRC y descartes (input drops) "
                    "en la interfaz ether1 (o Ethernet1/1)."
                ),
            ),
            (
                "Problemas de Carga Web y Pérdidas por Fragmentación MTU",
                (
                    "SÍNTOMA OPERACIONAL REPORTADO: Los clientes tienen pérdida de paquetes en conexiones HTTPS "
                    "y transferencias de archivos que se congelan debido a fragmentación de MTU."
                ),
            ),
            (
                "Tormenta de Broadcast y Saturación de CPU en la Red Local",
                (
                    "SÍNTOMA OPERACIONAL REPORTADO: El router reporta 95% de uso de CPU y switches parpadean. "
                    "Se sospecha de un bucle de red o tormenta de broadcast afectando el tráfico local en ether1."
                ),
            ),
            ("Describir un Síntoma Personalizado en Lenguaje Natural", "CUSTOM"),
        ]

        console.print("\n[bold cyan]📋 Selecciona el síntoma operacional a investigar:[/bold cyan]")
        for idx, (s_name, _) in enumerate(proactive_scenarios, 1):
            console.print(f"  [yellow]{idx}[/yellow]. [bold]{s_name}[/bold]")

        picked = prompt_choice(
            f"Elige el escenario [1-{len(proactive_scenarios)}]",
            choices=[str(i) for i in range(1, len(proactive_scenarios) + 1)],
            default="1",
        )
        chosen_idx = int(picked) - 1
        if proactive_scenarios[chosen_idx][1] == "CUSTOM":
            custom_symptom = prompt_non_empty(
                "Describe el síntoma (ej. 'Este router está teniendo pérdidas en la LAN en ether2')"
            )
            return f"SÍNTOMA OPERACIONAL REPORTADO POR EL OPERADOR:\n{custom_symptom}", "PROACTIVE"
        return proactive_scenarios[chosen_idx][1], "PROACTIVE"

    else:
        reactive_scenarios = [
            (
                "OSPF MTU Mismatch",
                "%OSPF-4-NONEIGHBOR: OSPF process 1, Neighbor 10.0.0.2 on interface Ethernet1/1 "
                "stuck in EXSTART/EXCHANGE state. Neighbor MTU 9216 is larger than local interface MTU 1500.",
            ),
            (
                "BGP Neighbor Down / Flapping",
                "%BGP-5-ADJCHANGE: neighbor 10.10.10.2 Down - BGP Notification sent, hold time expired",
            ),
            (
                "Interface Err-Disabled por Loop / BPDUGuard",
                "%PM-4-ERR_DISABLE: bpduguard error detected on Ethernet1/10, putting port in err-disable state",
            ),
            ("Syslog Personalizado (Pegar log exacto)", "CUSTOM"),
        ]

        console.print("\n[bold cyan]📋 Selecciona el evento de Syslog a simular:[/bold cyan]")
        for idx, (s_name, _) in enumerate(reactive_scenarios, 1):
            console.print(f"  [yellow]{idx}[/yellow]. [bold]{s_name}[/bold]")

        picked = prompt_choice(
            f"Elige el evento [1-{len(reactive_scenarios)}]",
            choices=[str(i) for i in range(1, len(reactive_scenarios) + 1)],
            default="1",
        )
        chosen_idx = int(picked) - 1
        if reactive_scenarios[chosen_idx][1] == "CUSTOM":
            custom_log = prompt_non_empty("Pega o escribe el log de telemetría")
            return custom_log, "REACTIVE"
        return reactive_scenarios[chosen_idx][1], "REACTIVE"
