"""Enterprise Closed-Loop Network Assistant Agent."""

from typing import Optional

from rich.panel import Panel
from rich.table import Table

from networking_agent.brains.factory import get_ai_brain
from networking_agent.core.audit import audit_logger
from networking_agent.core.config import settings
from networking_agent.core.exceptions import (
    BlastRadiusViolationError,
    CommandInjectionError,
)
from networking_agent.core.logging import console, logger
from networking_agent.drivers.factory import get_os_driver
from networking_agent.engine.verification import VerificationEngine
from networking_agent.guardrails.blast_radius import BlastRadiusGuard
from networking_agent.guardrails.validator import CommandValidator
from networking_agent.models.device import DeviceInventory
from networking_agent.models.intent import NetworkIntent
from networking_agent.models.telemetry import TelemetryEvent


class NetworkAssistantAgent:
    """Orchestrates closed-loop telemetry analysis, guardrail verification, HitL, and execution."""

    def __init__(
        self,
        ai_provider: Optional[str] = None,
        ai_model: Optional[str] = None,
        auto_approve: bool = False,
    ):
        self.brain = get_ai_brain(provider=ai_provider, model=ai_model)
        self.blast_guard = BlastRadiusGuard()
        self.auto_approve = auto_approve

    def process_telemetry(
        self,
        device: DeviceInventory,
        telemetry: TelemetryEvent,
        mode: str = "REACTIVE",
    ) -> bool:
        """Executes the closed-loop remediation workflow."""
        logger.info(
            f"\n[bold cyan][{mode}][/bold cyan] Ingesting telemetry for "
            f"[bold green]{device.host}[/bold green] ({device.device_type})..."
        )

        # 1. AI Diagnosis -> Neutral Intent
        intent: NetworkIntent = self.brain.analyze_event(telemetry.raw_text)

        # Display Diagnosis Panel
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

        # 2. Check if configuration change is needed
        if not intent.requires_config_change or intent.action == "none":
            logger.info("[green]No configuration changes required. Incident logged.[/green]")
            audit_logger.record_event(
                event_type="NO_OP",
                device_host=device.host,
                action=intent.action,
                commands=[],
                approved=True,
                extra={"diagnosis": intent.diagnosis},
            )
            return True

        # 3. Security Guardrails Verification (Blast Radius & Command Validation)
        try:
            self.blast_guard.verify_intent(intent)
        except BlastRadiusViolationError as e:
            audit_logger.record_event(
                event_type="SECURITY_REJECTED",
                device_host=device.host,
                action=intent.action,
                commands=[],
                approved=False,
                extra={"error": str(e)},
            )
            return False

        # 4. Driver translation to candidate CLI
        driver = get_os_driver(device)
        candidate_cli = driver.build_candidate_commands(intent)

        if not candidate_cli:
            logger.warning("[yellow]No CLI commands mapped for this action on this platform.[/yellow]")
            return False

        # Defense-in-depth: Validate all candidate commands
        try:
            candidate_cli = CommandValidator.validate_command_list(candidate_cli)
        except CommandInjectionError as e:
            audit_logger.record_event(
                event_type="INJECTION_REJECTED",
                device_host=device.host,
                action=intent.action,
                commands=candidate_cli,
                approved=False,
                extra={"error": str(e)},
            )
            return False

        # 5. Human-in-the-Loop (HitL) Approval Gate
        cli_preview = "\n".join([f"  + {c}" for c in candidate_cli])
        approval_panel = Panel(
            f"[bold red]WARNING: Configuration modification proposed on [white]{device.host}[/white][/bold red]\n\n"
            f"[bold yellow]Commands to be injected:[/bold yellow]\n{cli_preview}\n\n"
            f"[cyan]Action:[/cyan] {intent.action} | "
            f"[cyan]Target:[/cyan] {intent.target_interface or intent.bgp_neighbor_ip}",
            title="HUMAN-IN-THE-LOOP APPROVAL REQUIRED",
            border_style="red",
        )
        console.print(approval_panel)

        approved = False
        if self.auto_approve:
            logger.warning("[bold yellow]Auto-approve is enabled. Proceeding without prompt.[/bold yellow]")
            approved = True
        else:
            try:
                user_choice = input("Do you authorize injecting these changes? (y/N): ").strip().lower()
                approved = user_choice == "y" or user_choice == "yes" or user_choice == "s"
            except (EOFError, KeyboardInterrupt):
                approved = False

        if not approved:
            logger.info("[bold yellow][X] Operation rejected by operator. Device was NOT modified.[/bold yellow]")
            audit_logger.record_event(
                event_type="OPERATOR_REJECTED",
                device_host=device.host,
                action=intent.action,
                commands=candidate_cli,
                approved=False,
            )
            return False

        # 6. Pre-Check & Snapshot Backup
        logger.info("[*] Executing pre-change health snapshot...")
        backup_path = None
        pre_health = {}
        try:
            pre_health = driver.run_health_check()
            backup_path = driver.backup_running_config()
        except Exception as e:
            logger.error(f"[bold red]Pre-change safety checks failed: {e}[/bold red]")
            return False

        # 7. Apply Configuration
        logger.info("[*] Applying validated commands on device...")
        execution_output = ""
        try:
            execution_output = driver.execute_commands(candidate_cli)
        except Exception as e:
            logger.critical(f"[bold red]Execution error on {device.host}: {e}[/bold red]")
            if settings.auto_rollback_on_failure and backup_path:
                logger.warning("[yellow]Initiating emergency rollback...[/yellow]")
                driver.rollback(backup_path)
            audit_logger.record_event(
                event_type="EXECUTION_FAILED",
                device_host=device.host,
                action=intent.action,
                commands=candidate_cli,
                approved=True,
                execution_output=str(e),
                rollback_triggered=True,
            )
            return False

        # 8. Post-Check and Verification
        logger.info("[*] Running post-change health verification...")
        post_health = {}
        verification_passed = False
        try:
            post_health = driver.run_health_check()
            verification_passed = VerificationEngine.evaluate_changes(
                pre_state=pre_health,
                post_state=post_health,
                target_entity=intent.target_interface or "",
            )
        except Exception as e:
            logger.warning(f"[yellow]Health check evaluation failed: {e}[/yellow]")
            verification_passed = False

        if not verification_passed:
            logger.error("[bold red]Verification FAILED! Remediation did not resolve the problem.[/bold red]")
            if settings.auto_rollback_on_failure:
                logger.warning("[bold yellow]Triggering automated rollback...[/bold yellow]")
                driver.rollback(backup_path)
                audit_logger.record_event(
                    event_type="REMEDIATION_ROLLBACK",
                    device_host=device.host,
                    action=intent.action,
                    commands=candidate_cli,
                    approved=True,
                    verification_status="FAILED",
                    rollback_triggered=True,
                )
                return False

        # 9. Success Audit Record
        logger.info("[bold green][OK] Configuration successfully applied and verified in closed-loop.[/bold green]")
        audit_logger.record_event(
            event_type="REMEDIATION_SUCCESS",
            device_host=device.host,
            action=intent.action,
            commands=candidate_cli,
            approved=True,
            execution_output=execution_output,
            verification_status="PASSED",
            rollback_triggered=False,
        )
        return True
