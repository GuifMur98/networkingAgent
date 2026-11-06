"""Interactive configuration and onboarding wizard for NetworkingAgent."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import SecretStr
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from networking_agent.core.config import settings
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
    console.print(
        Panel(
            "[bold cyan]🧠 Configuración Interactiva del Cerebro de Inteligencia Artificial[/bold cyan]\n"
            "Elige el proveedor de IA y el modelo a utilizar para diagnosticar eventos de red.",
            border_style="cyan",
        )
    )

    # 1. Selection of AI Provider
    providers = [
        ("ollama", "Ollama (Inferencia 100% Local y Privada en tu máquina)"),
        ("gemini", "Google Gemini (Gemini 3.8 Flash / Argon vía Cloud API)"),
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

    prov_choice = Prompt.ask(
        "Selecciona el proveedor de IA [1-4]",
        choices=["1", "2", "3", "4"],
        default="1"
        if not default_provider
        else str(
            [p[0] for p in providers].index(default_provider) + 1
            if default_provider in [p[0] for p in providers]
            else "1"
        ),
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

            # Recommend specialized models first (e.g., netexpert)
            for idx, m in enumerate(installed_models, 1):
                star = " 🌟 (Recomendado para Redes)" if "netexpert" in m["name"].lower() else ""
                model_table.add_row(str(idx), f"{m['name']}{star}", m["size"])
            console.print(model_table)

            choices = [str(i) for i in range(1, len(installed_models) + 1)]
            choices.append("c")  # Custom

            # Determine best default choice
            default_idx = "1"
            for idx, m in enumerate(installed_models, 1):
                if "netexpert" in m["name"].lower():
                    default_idx = str(idx)
                    break

            picked = Prompt.ask(
                f"Selecciona el modelo a usar [1-{len(installed_models)}] o 'c' para ingresar otro",
                choices=choices,
                default=default_idx,
            )

            if picked == "c":
                selected_model = Prompt.ask("Ingresa el nombre exacto del modelo en Ollama")
            else:
                selected_model = installed_models[int(picked) - 1]["name"]
        else:
            console.print("[yellow]No se detectaron modelos activos en Ollama o el servicio no respondió.[/yellow]")
            selected_model = Prompt.ask("Ingresa el nombre del modelo de Ollama a utilizar", default="llama3.1")

    # 3. Model selection for Google Gemini
    elif selected_provider == "gemini":
        if not (os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key):
            api_key = Prompt.ask("Ingresa tu GEMINI_API_KEY", password=True)
            os.environ["GEMINI_API_KEY"] = api_key

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
        m_idx = Prompt.ask("Selecciona modelo", choices=["1", "2", "3", "4"], default="1")
        if m_idx == "4":
            selected_model = Prompt.ask("Ingresa el identificador del modelo (ej. gemini-3.8-flash)")
        else:
            selected_model = gemini_models[int(m_idx) - 1]

    # 4. Model selection for OpenAI
    elif selected_provider == "openai":
        # Check API key
        if not (os.environ.get("OPENAI_API_KEY") or settings.openai_api_key):
            api_key = Prompt.ask("Ingresa tu OPENAI_API_KEY", password=True)
            os.environ["OPENAI_API_KEY"] = api_key

        console.print("\n[bold]Modelos de OpenAI disponibles:[/bold]")
        openai_models = ["gpt-4o", "gpt-4o-mini", "o1-mini", "Personalizado"]
        for idx, m in enumerate(openai_models, 1):
            console.print(f"  [yellow]{idx}[/yellow]. {m}")
        m_idx = Prompt.ask("Selecciona modelo", choices=["1", "2", "3", "4"], default="1")
        if m_idx == "4":
            selected_model = Prompt.ask("Ingresa el identificador del modelo")
        else:
            selected_model = openai_models[int(m_idx) - 1]

    # 4. Model selection for Anthropic
    else:
        # Check API key
        if not (os.environ.get("ANTHROPIC_API_KEY") or settings.anthropic_api_key):
            api_key = Prompt.ask("Ingresa tu ANTHROPIC_API_KEY", password=True)
            os.environ["ANTHROPIC_API_KEY"] = api_key

        console.print("\n[bold]Modelos de Anthropic disponibles:[/bold]")
        anthropic_models = [
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "Personalizado",
        ]
        for idx, m in enumerate(anthropic_models, 1):
            console.print(f"  [yellow]{idx}[/yellow]. {m}")
        m_idx = Prompt.ask("Selecciona modelo", choices=["1", "2", "3"], default="1")
        if m_idx == "3":
            selected_model = Prompt.ask("Ingresa el identificador del modelo")
        else:
            selected_model = anthropic_models[int(m_idx) - 1]

    console.print(f"\n[green]✓ Cerebro configurado:[/green] [bold]{selected_provider} / {selected_model}[/bold]\n")
    return selected_provider, selected_model


def configure_device_interactively(
    default_host: Optional[str] = None,
    default_type: Optional[str] = None,
) -> DeviceInventory:
    """Prompts the user interactively to configure target device credentials."""
    console.print(
        Panel(
            "[bold cyan]🔌 Configuración de Conexión al Dispositivo de Red[/bold cyan]\n"
            "Ingresa los parámetros SSH del equipo que será monitoreado y remediado.",
            border_style="cyan",
        )
    )

    # 1. Device Host
    host = Prompt.ask(
        "Dirección IP o FQDN del dispositivo",
        default=default_host or os.environ.get("NET_HOST", "10.10.20.11"),
    )

    # 2. Platform / OS Selection
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

    plat_choice = Prompt.ask(
        "Selecciona el Sistema Operativo del equipo [1-5]",
        choices=["1", "2", "3", "4", "5"],
        default="1"
        if not default_type
        else str(
            [p[0] for p in platforms].index(default_type) + 1 if default_type in [p[0] for p in platforms] else "1"
        ),
    )
    selected_platform = platforms[int(plat_choice) - 1][0]

    # 3. Port
    port = IntPrompt.ask("Puerto SSH", default=22)

    # 4. Username
    username = Prompt.ask(
        "Usuario SSH",
        default=os.environ.get("NET_USER", "admin"),
    )

    # 5. Authentication Type
    auth_type = Prompt.ask(
        "Tipo de autenticación SSH",
        choices=["password", "key"],
        default="password",
    )

    password: Optional[SecretStr] = None
    secret: Optional[SecretStr] = None
    key_file: Optional[str] = None
    use_keys = False

    if auth_type == "password":
        existing_pass = os.environ.get("NET_PASS")
        if existing_pass:
            use_existing = Confirm.ask(
                "¿Deseas usar la contraseña definida en la variable de entorno NET_PASS?", default=True
            )
            if use_existing:
                password = SecretStr(existing_pass)

        if not password:
            raw_pass = Prompt.ask("Ingresa la contraseña SSH del equipo", password=True)
            password = SecretStr(raw_pass) if raw_pass else None

        has_enable = Confirm.ask(
            "¿El equipo requiere contraseña de modo privilegiado (enable secret)?",
            default=False,
        )
        if has_enable:
            raw_secret = Prompt.ask("Ingresa el enable secret", password=True)
            secret = SecretStr(raw_secret) if raw_secret else None
    else:
        use_keys = True
        key_file = Prompt.ask(
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

    console.print(
        f"\n[green]✓ Dispositivo configurado:[/green] [bold]{device.host}[/bold] "
        f"([cyan]{device.device_type}[/cyan]) con usuario [bold]{device.username}[/bold]\n"
    )
    return device


def prompt_telemetry_event() -> str:
    """Allows selecting a real-world scenario or typing custom telemetry."""
    scenarios = [
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
            "%PM-4-ERR_DISABLE: bpduguard error detected on Ethernet1/10, putting Ethernet1/10 in err-disable state",
        ),
        ("Evento Personalizado (Escribir o pegar log manual)", "CUSTOM"),
    ]

    console.print("[bold cyan]📋 Selecciona el Evento de Telemetría o Syslog a Simular:[/bold cyan]")
    for idx, (s_name, s_log) in enumerate(scenarios, 1):
        preview = f": {s_log[:70]}..." if s_log != "CUSTOM" else ""
        console.print(f"  [yellow]{idx}[/yellow]. [bold]{s_name}[/bold]{preview}")

    scen_choice = Prompt.ask("Elige el escenario [1-4]", choices=["1", "2", "3", "4"], default="1")
    chosen_idx = int(scen_choice) - 1

    if scenarios[chosen_idx][1] == "CUSTOM":
        return Prompt.ask("Pega o escribe el log de telemetría")
    return scenarios[chosen_idx][1]
