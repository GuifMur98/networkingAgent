"""CLI Entrypoint for the Networking Agent with both Interactive Wizard and Batch modes."""

import argparse
import os
import sys

from pydantic import SecretStr
from rich.panel import Panel

from networking_agent.cli.interactive import (
    configure_device_interactively,
    display_main_menu,
    manage_devices_interactively,
    prompt_telemetry_event,
    select_ai_brain_interactively,
    view_audit_trail_interactively,
)
from networking_agent.cli.prompts import prompt_choice
from networking_agent.cli.ui_theme import print_execution_summary
from networking_agent.core.db import db
from networking_agent.core.logging import console
from networking_agent.engine.agent import NetworkAssistantAgent
from networking_agent.models.device import DeviceInventory
from networking_agent.models.telemetry import TelemetryEvent


def cli_entrypoint() -> None:
    """Parses command-line arguments and runs the agent."""
    parser = argparse.ArgumentParser(description="NetworkingAgent: Enterprise Closed-Loop Network Assistant")
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Iniciar la interfaz de usuario reactiva en terminal (Textual TUI)",
    )
    parser.add_argument(
        "-c",
        "--cli",
        action="store_true",
        help="Iniciar el asistente interactivo clásico de consola por pasos",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Iniciar en modo asistente interactivo clásico (detecta modelos y solicita credenciales)",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "gemini", "openai", "anthropic"],
        default=None,
        help="Proveedor de IA a utilizar",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Nombre específico del modelo (ej. netexpert:latest, gemini-3.8-flash, gpt-4o, claude-3-5-sonnet-latest)",
    )
    parser.add_argument(
        "--device-host",
        type=str,
        default=None,
        help="IP o hostname del dispositivo de red",
    )
    parser.add_argument(
        "--device-type",
        type=str,
        default=None,
        help="Plataforma de red (cisco_nxos, cisco_ios, cisco_xr, juniper_junos, mikrotik_routeros)",
    )
    parser.add_argument(
        "--mode",
        choices=["REACTIVE", "PROACTIVE"],
        default="REACTIVE",
        help="Modo de ejecución: REACTIVE (analizar syslog) o PROACTIVE (investigar síntoma/pérdidas)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Omitir confirmación manual HitL (usar con precaución en laboratorio)",
    )
    parser.add_argument(
        "--log-message",
        type=str,
        default=None,
        help="Mensaje de log o evento de telemetría a diagnosticar",
    )

    args = parser.parse_args()

    # Determine whether to launch Textual TUI:
    # 1. Explicitly requested with --tui
    # 2. Default behavior: interactive terminal session without batch flags or --cli/-i
    has_batch_args = bool(args.provider or args.device_host or args.log_message)
    should_launch_tui = args.tui or (not args.cli and not args.interactive and not has_batch_args)

    if should_launch_tui:
        from networking_agent.tui import run_tui

        run_tui()
        sys.exit(0)

    # Determine whether to run classic CLI interactively:
    # If -i or -c is passed, or if neither provider nor device-host was supplied via CLI:
    is_interactive = args.cli or args.interactive or (args.provider is None and args.device_host is None)

    if is_interactive:
        while True:
            choice = display_main_menu()

            if choice == "1":
                # Option 1: Iniciar Diagnóstico y Remediación Asistida
                provider = args.provider or db.get_setting("ai_provider") or "ollama"
                model = args.model or db.get_setting("ai_model") or "qwen2.5-coder:7b"

                device = configure_device_interactively(
                    default_host=args.device_host,
                    default_type=args.device_type,
                    allow_back=True,
                )
                if not device:
                    continue

                while True:
                    if args.log_message:
                        log_text = args.log_message
                        run_mode = args.mode or "REACTIVE"
                        one_shot = True
                    else:
                        log_text, run_mode = prompt_telemetry_event(allow_back=True)
                        one_shot = False

                    if not log_text or not run_mode:
                        break

                    print_execution_summary(
                        provider=provider,
                        model=model,
                        device_host=device.host,
                        device_type=device.device_type,
                        device_user=device.username,
                        mode=run_mode,
                        symptom_summary=log_text,
                    )

                    event = TelemetryEvent(raw_text=log_text, source_host=device.host)
                    agent = NetworkAssistantAgent(
                        ai_provider=provider,
                        ai_model=model,
                        auto_approve=args.auto_approve,
                    )
                    agent.process_telemetry(device=device, telemetry=event, mode=run_mode)

                    if one_shot:
                        break

                    # Continuity & Navigation Menu
                    console.print("\n")
                    continuity_panel = Panel(
                        f"[bold cyan]El análisis ha finalizado.[/bold cyan] ¿Cómo deseas continuar?\n\n"
                        f"  [yellow]1[/yellow]. [bold green]Diagnosticar otro sintoma o log en este mismo equipo "
                        f"({device.host})[/bold green]\n"
                        f"  [yellow]2[/yellow]. [bold blue]Cambiar de equipo de red[/bold blue]\n"
                        f"  [yellow]3[/yellow]. [bold magenta]Volver al Menu Principal[/bold magenta]\n"
                        f"  [yellow]4[/yellow]. [bold red]Salir del asistente[/bold red]",
                        title="CONTINUIDAD DE OPERACIONES Y DIAGNOSTICO",
                        border_style="cyan",
                    )
                    console.print(continuity_panel)

                    next_action = prompt_choice(
                        "Selecciona una opción [1-4]",
                        choices=["1", "2", "3", "4"],
                        default="3",
                    )

                    if next_action == "1":
                        console.print(f"\n[green]Continuando diagnóstico sobre [bold]{device.host}[/bold]...[/green]\n")
                        continue
                    elif next_action == "2":
                        device = configure_device_interactively(allow_back=True)
                        if not device:
                            break
                        continue
                    elif next_action == "3":
                        break
                    elif next_action == "4":
                        console.print(
                            "\n[bold green][OK] Sesion finalizada con exito. "
                            "¡Gracias por usar NetworkingAgent![/bold green]\n"
                        )
                        sys.exit(0)

            elif choice == "2":
                manage_devices_interactively()

            elif choice == "3":
                select_ai_brain_interactively(allow_back=True)

            elif choice == "4":
                view_audit_trail_interactively()

            elif choice == "5":
                console.print(
                    "\n[bold green][OK] Sesion finalizada con exito. Gracias por usar NetworkingAgent.[/bold green]\n"
                )
                sys.exit(0)
    else:
        # Non-interactive CLI flags mode
        provider = args.provider or os.environ.get("AI_PROVIDER", "ollama")
        model = args.model or os.environ.get("AI_MODEL", "llama3.1")
        host = args.device_host or os.environ.get("NET_HOST", "10.10.20.11")
        dev_type = args.device_type or os.environ.get("NET_TYPE", "cisco_nxos")
        run_mode = args.mode or "REACTIVE"

        net_pass = os.environ.get("NET_PASS")
        device = DeviceInventory(
            host=host,
            device_type=dev_type,  # type: ignore
            username=os.environ.get("NET_USER", "admin"),
            password=SecretStr(net_pass) if net_pass else None,
        )

        log_text = args.log_message or (
            "%OSPF-4-NONEIGHBOR: OSPF process 1, Neighbor 10.0.0.2 on interface Ethernet1/1 "
            "stuck in EXSTART/EXCHANGE state. Neighbor MTU 9216 is larger than local interface MTU 1500."
        )
        event = TelemetryEvent(raw_text=log_text, source_host=device.host)
        agent = NetworkAssistantAgent(
            ai_provider=provider,
            ai_model=model,
            auto_approve=args.auto_approve,
        )
        success = agent.process_telemetry(device=device, telemetry=event, mode=run_mode)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    cli_entrypoint()
