"""Observer interfaces and implementations for event notifications during closed-loop execution."""

from typing import List, Protocol

from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from networking_agent.cli.prompts import prompt_hitl_approval
from networking_agent.core.logging import console, logger
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent


class AgentObserver(Protocol):
    """Protocol defining UI and event callbacks for the closed-loop agent."""

    def on_status_update(self, message: str) -> None: ...

    def on_diagnosis_ready(self, intent: NetworkIntent) -> None: ...

    def on_no_op_required(self, device: DeviceInventory, intent: NetworkIntent) -> None: ...

    def on_guardrail_blocked(self, intent: NetworkIntent, reason: str) -> None: ...

    def on_hitl_approval_required(
        self,
        device: DeviceInventory,
        intent: NetworkIntent,
        candidate_cli: List[str],
        rollback_info: str,
    ) -> bool: ...

    def on_execution_progress(self, step: str) -> None: ...

    def on_progress(self, percentage: int, step: str) -> None: ...

    def on_completion(self, success: bool, message: str) -> None: ...


class ConsoleAgentObserver:
    """Default observer implementing the rich CLI user experience."""

    def on_status_update(self, message: str) -> None:
        logger.info(message)

    def on_diagnosis_ready(self, intent: NetworkIntent) -> None:
        table = Table(title="AI Diagnostic Assessment", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="dim", width=24)
        table.add_column("Value", style="bold")
        table.add_row("Severity", f"[{'red' if intent.severity == 'CRITICAL' else 'yellow'}]{intent.severity}[/]")
        table.add_row("Root Cause Diagnosis", intent.diagnosis)
        table.add_row("Proposed Action", intent.action)
        table.add_row("Requires Config Change", str(intent.requires_config_change))
        if intent.target_interface:
            table.add_row("Target Interface", intent.target_interface)
        if intent.mtu_value:
            table.add_row("MTU Value", str(intent.mtu_value))
        if intent.bgp_neighbor_ip:
            table.add_row("BGP Neighbor IP", intent.bgp_neighbor_ip)
        console.print(table)

    def on_no_op_required(self, device: DeviceInventory, intent: NetworkIntent) -> None:
        findings_panel = Panel(
            f"[bold green][OK] EVALUACION DIAGNOSTICA TECNICA COMPLETADA[/bold green]\n\n"
            f"[bold cyan]Diagnóstico de Causa Raíz:[/bold cyan]\n"
            f"{intent.diagnosis}\n\n"
            f"[bold yellow]Estado de Configuración:[/bold yellow] No se requieren cambios en el equipo.\n"
            f"[dim]Severidad: {intent.severity} | Acción: {intent.action} | Equipo: {device.host}[/dim]",
            title="INFORME OPERACIONAL DEL ASISTENTE DE RED",
            border_style="green",
        )
        console.print(findings_panel)

    def on_guardrail_blocked(self, intent: NetworkIntent, reason: str) -> None:
        shield_panel = Panel(
            f"[bold red][ALERTA] ACCION BLOQUEADA POR GUARDARAIL DE SEGURIDAD (BLAST RADIUS)[/bold red]\n\n"
            f"[yellow]El cerebro de IA propuso una modificación de riesgo:[/yellow]\n"
            f"  • Acción solicitada: [bold red]{intent.action}[/bold red]\n"
            f"  • Interfaz Objetivo: [bold yellow]{escape(intent.target_interface or 'N/A')}[/bold yellow]\n\n"
            f"[bold cyan]Motivo de Protección:[/bold cyan]\n"
            f"{escape(reason)}\n\n"
            f"[green]Recomendación de Seguridad:[/green]\n"
            f"Las interfaces WAN / Enlace Ascendente están blindadas contra reinicios remotos.\n"
            f"Para lentitud o caídas en la WAN, verifique el cableado/óptica física o contacte al ISP.",
            title="SEGURIDAD ACTIVA: PROTECCION DE INFRAESTRUCTURA CRITICA",
            border_style="bold red",
        )
        console.print(shield_panel)

    def on_hitl_approval_required(
        self,
        device: DeviceInventory,
        intent: NetworkIntent,
        candidate_cli: List[str],
        rollback_info: str,
    ) -> bool:
        target_display = escape(str(intent.target_interface or intent.bgp_neighbor_ip or "N/A"))
        sev_color = "red" if intent.severity == "CRITICAL" else "yellow"
        cli_preview = "\n".join(
            [f"  [bold green]+[/bold green] [white]{escape(str(c))}[/white]" for c in candidate_cli]
        )
        approval_panel = Panel(
            f"[bold red][SEGURIDAD] SOLICITUD DE AUTORIZACION OBLIGATORIA (HUMAN-IN-THE-LOOP)[/bold red]\n\n"
            f"El motor de remediación autónoma propone aplicar cambios en la configuración activa.\n"
            f"• [bold cyan]Equipo Destino:[/] {escape(str(device.host))} ({escape(str(device.device_type))})\n"
            f"• [bold cyan]Diagnóstico:[/bold cyan] {escape(str(intent.diagnosis))}\n"
            f"• [bold cyan]Severidad:[/] [{sev_color}]{intent.severity}[/{sev_color}]\n"
            f"• [bold cyan]Acción Solicitada:[/] [bold]{escape(str(intent.action))}[/bold]\n"
            f"• [bold cyan]Parámetro Afectado:[/] {target_display}\n\n"
            f"[bold yellow]Comandos CLI candidatos a inyectar:[/bold yellow]\n{cli_preview}\n\n"
            f"[bold blue]Estrategia de Rollback / Reversión:[/bold blue]\n{escape(str(rollback_info))}",
            title="HITL APPROVAL GATE",
            border_style="bold red",
        )
        console.print(approval_panel)
        return prompt_hitl_approval()

    def on_execution_progress(self, step: str) -> None:
        logger.info(step)

    def on_progress(self, percentage: int, step: str) -> None:
        logger.info(f"[{percentage}%] {step}")

    def on_completion(self, success: bool, message: str) -> None:
        if success:
            console.print(
                Panel(
                    f"[bold green]{message}[/bold green]",
                    title="OPERACION EXITOSA",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]{message}[/bold red]",
                    title="FALLO EN LA OPERACION",
                    border_style="red",
                )
            )
