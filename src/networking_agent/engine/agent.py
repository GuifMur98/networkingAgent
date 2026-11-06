"""Enterprise Closed-Loop Network Assistant Agent."""

from typing import Optional

from networking_agent.brains.factory import get_ai_brain
from networking_agent.core.audit import audit_logger
from networking_agent.core.config import settings
from networking_agent.core.exceptions import (
    BlastRadiusViolationError,
    CommandInjectionError,
)
from networking_agent.core.logging import logger
from networking_agent.drivers.factory import get_os_driver
from networking_agent.engine.observer import AgentObserver, ConsoleAgentObserver
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
        observer: Optional[AgentObserver] = None,
    ):
        self.brain = get_ai_brain(provider=ai_provider, model=ai_model)
        self.blast_guard = BlastRadiusGuard()
        self.auto_approve = auto_approve
        self.observer = observer or ConsoleAgentObserver()

    def process_telemetry(
        self,
        device: DeviceInventory,
        telemetry: TelemetryEvent,
        mode: str = "REACTIVE",
    ) -> bool:
        """Executes the closed-loop remediation workflow."""
        self.observer.on_status_update(
            f"[{mode}] Ingesting telemetry for {device.host} ({device.device_type})..."
        )

        analysis_payload = telemetry.raw_text
        driver = get_os_driver(device)
        try:
            health_data = {}

            if mode == "PROACTIVE":
                self.observer.on_status_update("[*] Running proactive diagnostic interrogation on device...")
                try:
                    health_data = driver.run_health_check()
                    telemetry_str = "\n".join([f"=== {cmd} ===\n{out}" for cmd, out in health_data.items()])
                    wan_interfaces = driver.discover_active_management_interfaces(health_data)
                    analysis_payload = (
                        f"DEVICE ARCHITECTURE CONTEXT:\n"
                        f"Host: {device.host} | OS: {device.device_type}\n"
                        f"Protected WAN / Gateway / Management Interfaces: {', '.join(wan_interfaces)}\n\n"
                        f"OPERATIONAL SYMPTOM REPORTED BY OPERATOR:\n{telemetry.raw_text}\n\n"
                        f"LIVE DEVICE DIAGNOSTIC TELEMETRY:\n{telemetry_str}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[yellow]Could not fetch live device diagnostics ({e}); "
                        "proceeding with reported symptom description.[/yellow]"
                    )
                    wan_interfaces = driver.discover_active_management_interfaces()
            else:
                wan_interfaces = driver.discover_active_management_interfaces()

            # 1. AI Diagnosis -> Neutral Intent
            intent: NetworkIntent = self.brain.analyze_event(analysis_payload)

            # Display Diagnosis Panel via Observer
            self.observer.on_diagnosis_ready(intent)

            # 2. Check if configuration change is needed
            if not intent.requires_config_change or intent.action == "none":
                self.observer.on_no_op_required(device, intent)
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
                self.blast_guard.verify_intent(intent, wan_interfaces=wan_interfaces)
            except BlastRadiusViolationError as e:
                self.observer.on_guardrail_blocked(intent, str(e))
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
            rollback_info = driver.get_rollback_description()
            approved = False
            if self.auto_approve:
                logger.warning(
                    "[bold red]ATENCIÓN: Modo auto-approve activo. Omitiendo confirmación humana.[/bold red]"
                )
                approved = True
            else:
                approved = self.observer.on_hitl_approval_required(
                    device=device,
                    intent=intent,
                    candidate_cli=candidate_cli,
                    rollback_info=rollback_info,
                )

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
            self.observer.on_execution_progress("[*] Executing pre-change health snapshot...")
            backup_path = None
            pre_health = {}
            try:
                pre_health = driver.run_health_check()
                backup_path = driver.backup_running_config()
            except Exception as e:
                logger.error(f"[bold red]Pre-change safety checks failed: {e}[/bold red]")
                self.observer.on_completion(False, f"Pre-change safety checks failed: {e}")
                return False

            # 7. Apply Configuration
            self.observer.on_execution_progress("[*] Applying validated commands on device...")
            execution_output = ""
            try:
                execution_output = driver.execute_commands(candidate_cli)
            except Exception as e:
                logger.critical(f"[bold red]Execution error on {device.host}: {e}[/bold red]")
                if settings.auto_rollback_on_failure and backup_path:
                    self.observer.on_execution_progress("[yellow]Initiating emergency rollback...[/yellow]")
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
                self.observer.on_completion(False, f"Execution error: {e}")
                return False

            # 8. Post-Check and Verification
            self.observer.on_execution_progress("[*] Running post-change health verification...")
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
                    self.observer.on_execution_progress("[bold yellow]Triggering automated rollback...[/bold yellow]")
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
                    self.observer.on_completion(False, "Remediation verification failed; device rolled back.")
                    return False

            # 9. Success Audit Record
            logger.info(
                "[bold green][OK] Configuration successfully applied and verified in closed-loop.[/bold green]"
            )
            self.observer.on_completion(
                True, "Configuration successfully applied and verified in closed-loop."
            )
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
        finally:
            driver.disconnect()
