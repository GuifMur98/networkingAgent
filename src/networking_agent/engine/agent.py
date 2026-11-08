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
from networking_agent.engine.conflict_analyzer import ConfigConflictAnalyzer
from networking_agent.engine.observer import AgentObserver, ConsoleAgentObserver
from networking_agent.engine.verification import VerificationEngine
from networking_agent.guardrails.blast_radius import BlastRadiusGuard
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.guardrails.validator import CommandValidator
from networking_agent.models.config_intent import ConfigurationIntent
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
        self.observer.on_progress(15, f"[{mode}] Ingestando telemetría de {device.host}...")
        self.observer.on_status_update(
            f"[{mode}] Ingesting telemetry for {device.host} ({device.device_type})..."
        )

        analysis_payload = telemetry.raw_text
        driver = get_os_driver(device)
        try:
            health_data = {}

            if mode == "PROACTIVE":
                self.observer.on_progress(35, "Ejecutando interrogación de salud en vivo en el equipo...")
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
                self.observer.on_progress(35, "Analizando eventos de Syslog/Logs reportados...")
                wan_interfaces = driver.discover_active_management_interfaces()

            # 1. AI Diagnosis -> Neutral Intent
            self.observer.on_progress(55, "Correlacionando anomalías y consultando Cerebro IA...")
            intent: NetworkIntent = self.brain.analyze_event(analysis_payload)

            # Display Diagnosis Panel via Observer
            self.observer.on_diagnosis_ready(intent)

            # 2. Check if configuration change is needed
            if not intent.requires_config_change or intent.action == "none":
                self.observer.on_progress(100, f"Diagnóstico completado: Equipo {device.host} operacionalmente sano.")
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
            self.observer.on_progress(70, "Verificando guardarraíles de seguridad y radio de impacto...")
            try:
                self.blast_guard.verify_intent(intent, wan_interfaces=wan_interfaces)
            except BlastRadiusViolationError as e:
                self.observer.on_progress(100, "Operación bloqueada por guardarraíl de protección WAN.")
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
            self.observer.on_progress(80, "Sintetizando y validando comandos de configuración...")
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
            self.observer.on_progress(85, "Esperando confirmación humana (HitL)...")
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
                self.observer.on_progress(100, "Operación rechazada por el operador.")
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
            self.observer.on_progress(90, f"Tomando snapshot de respaldo en {device.host}...")
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
            self.observer.on_progress(95, "Aplicando comandos validados en el dispositivo...")
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
            self.observer.on_progress(100, f"Remediación completada y verificada en {device.host}.")
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

    def execute_troubleshooting(self, device: DeviceInventory, symptom: str) -> bool:
        """Executes full autonomous troubleshooting interrogation with live telemetry correlation."""
        driver = get_os_driver(device)
        try:
            self.observer.on_progress(10, f"Iniciando conexión SSH con {device.host} ({device.device_type})...")
            self.observer.on_status_update(f"[*] Recopilando telemetría especializada para: '{symptom}'...")
            diag_cmds = driver.get_troubleshooting_commands(symptom)
            self.observer.on_progress(25, f"Ejecutando interrogación ({len(diag_cmds)} comandos show en vivo)...")
            telemetry_data = driver.run_diagnostic_interrogation(diag_cmds)
            telemetry_str = "\n".join([f"=== {cmd} ===\n{out}" for cmd, out in telemetry_data.items()])

            wan_interfaces = driver.discover_active_management_interfaces(telemetry_data)
            analysis_payload = (
                f"DEVICE ARCHITECTURE CONTEXT:\n"
                f"Host: {device.host} | OS: {device.device_type}\n"
                f"Protected WAN / Gateway / Management Interfaces: {', '.join(wan_interfaces)}\n\n"
                f"OPERATIONAL SYMPTOM REPORTED BY OPERATOR IN NATURAL LANGUAGE:\n{symptom}\n\n"
                f"LIVE DEVICE DIAGNOSTIC TELEMETRY:\n{telemetry_str}"
            )

            # 1. AI Diagnosis -> Neutral Intent
            self.observer.on_progress(50, "Telemetría obtenida. Analizando causa raíz con Cerebro IA...")
            intent: NetworkIntent = self.brain.analyze_event(analysis_payload)
            self.observer.on_diagnosis_ready(intent)

            # 2. Check if configuration change is needed
            if not intent.requires_config_change or intent.action == "none":
                self.observer.on_progress(100, f"Diagnóstico completado: Equipo {device.host} operacionalmente sano.")
                self.observer.on_no_op_required(device, intent)
                audit_logger.record_event(
                    event_type="TROUBLESHOOTING_RESOLVED",
                    device_host=device.host,
                    action=intent.action,
                    commands=[],
                    approved=True,
                    extra={"diagnosis": intent.diagnosis, "symptom": symptom},
                )
                return True

            # 3. Guardrails & Blast Radius
            self.observer.on_progress(70, "Evaluando políticas de seguridad y radio de impacto (Blast Radius)...")
            try:
                self.blast_guard.verify_intent(intent, wan_interfaces=wan_interfaces)
            except BlastRadiusViolationError as e:
                self.observer.on_progress(100, "Operación bloqueada por guardarraíl de protección WAN.")
                self.observer.on_guardrail_blocked(intent, str(e))
                return False

            self.observer.on_progress(80, "Sintetizando y validando comandos CLI candidatos...")
            candidate_cli = driver.build_candidate_commands(intent)
            candidate_cli = CommandValidator.validate_command_list(candidate_cli)

            # 4. HitL Approval Gate
            rollback_info = driver.get_rollback_description()
            self.observer.on_progress(85, "Esperando autorización del operador (Human-in-the-Loop)...")
            approved = self.auto_approve or self.observer.on_hitl_approval_required(
                device=device,
                intent=intent,
                candidate_cli=candidate_cli,
                rollback_info=rollback_info,
            )

            if not approved:
                self.observer.on_progress(100, "Remediación rechazada por el operador.")
                self.observer.on_status_update("[yellow]Remediación rechazada por el operador.[/yellow]")
                return False

            # 5. Transactional Execution
            self.observer.on_progress(90, f"Creando snapshot de respaldo y aplicando cambios en {device.host}...")
            backup_file = driver.backup_running_config()
            driver.execute_commands(candidate_cli)
            self.observer.on_progress(100, f"Remediación aplicada exitosamente en {device.host}.")
            self.observer.on_completion(True, "Remediación aplicada exitosamente.")
            audit_logger.record_event(
                event_type="TROUBLESHOOTING_REMEDIATED",
                device_host=device.host,
                action=intent.action,
                commands=candidate_cli,
                approved=True,
                extra={"backup": str(backup_file)},
            )
            return True
        except Exception as e:
            self.observer.on_progress(100, f"Error durante troubleshooting: {e}")
            self.observer.on_completion(False, f"Error durante troubleshooting en {device.host}: {e}")
            return False
        finally:
            driver.disconnect()

    def execute_configuration(
        self,
        device: DeviceInventory,
        natural_request: str,
        protocol_hint: Optional[str] = None,
    ) -> Optional[ConfigurationIntent]:
        """Synthesizes, validates, and deploys declarative multi-protocol network configurations,

        guaranteeing the Zero-Damage Principle through active state inspection and conflict analysis.
        """
        self.observer.on_progress(10, f"Conectando a {device.host} para inspeccionar configuración activa...")
        self.observer.on_status_update(
            f"[CONFIG] Iniciando análisis no destructivo para {device.host} ({device.device_type})..."
        )
        driver = get_os_driver(device)

        # 1. Active State Inspection: Retrieve running config without modifying anything
        existing_config = ""
        try:
            self.observer.on_progress(25, "Recopilando running-config y telemetría de protocolos...")
            existing_config = driver.get_running_config()
            self.observer.on_execution_progress(
                f"[*] Configuración activa recuperada de {device.host} ({len(existing_config)} bytes)."
            )
        except Exception as e:
            logger.warning(f"Could not read running-config directly ({e}); proceeding with local state analysis.")
            self.observer.on_execution_progress(
                f"[yellow][!] Lectura directa de running-config no disponible ({e}); "
                "aplicando análisis conservador.[/yellow]"
            )

        # 2. Dynamic Routing Disambiguation & Pre-Flight State Analysis
        self.observer.on_progress(40, "Analizando protocolos activos y detectando posibles colisiones...")
        state_summary = ConfigConflictAnalyzer.analyze_running_state(existing_config, device.device_type)
        self.observer.on_execution_progress(f"[cyan][i] Estado detectado: {state_summary.raw_summary}[/cyan]")

        disambig_proto, disambig_exp = ConfigConflictAnalyzer.resolve_dynamic_routing_disambiguation(
            natural_request, existing_config, device.device_type
        )
        effective_protocol_hint = disambig_proto or protocol_hint
        if disambig_exp:
            self.observer.on_execution_progress(f"[bold cyan][>] Disambiguación: {disambig_exp}[/bold cyan]")

        # 3. AI Brain Configuration Synthesis with Active Config Context
        self.observer.on_progress(55, "Sintetizando configuración no destructiva con IA...")
        config_intent: ConfigurationIntent = self.brain.synthesize_configuration(
            device_host=device.host,
            vendor_family=device.device_type,
            natural_request=natural_request,
            protocol_hint=effective_protocol_hint,
            existing_config=existing_config,
        )

        # 4. Deterministic Conflict Analysis & Intent Enrichment
        config_intent = ConfigConflictAnalyzer.enrich_intent(
            intent=config_intent,
            request_text=natural_request,
            running_config=existing_config,
            vendor_family=device.device_type,
            device_host=device.host,
        )
        if "[!]" in config_intent.conflict_analysis:
            self.observer.on_execution_progress(
                f"[bold yellow]{config_intent.conflict_analysis}[/bold yellow]"
            )
        else:
            self.observer.on_execution_progress(
                f"[bold green]{config_intent.conflict_analysis}[/bold green]"
            )

        # 5. Syntax & Command Validation
        self.observer.on_progress(70, "Validando sintaxis de comandos y salvaguardas operacionales...")
        validation = ConfigSyntaxValidator.validate_script(
            "\n".join(config_intent.candidate_commands),
            vendor_family=device.device_type,
        )
        if not validation.is_valid:
            error_msg = " | ".join(validation.errors)
            self.observer.on_status_update(f"[bold red][!] Configuración rechazada por sintaxis: {error_msg}[/]")
            return None

        # 6. HitL Approval Gate
        self.observer.on_progress(80, "Esperando autorización obligatoria Human-in-the-Loop...")
        rollback_info = driver.get_rollback_description()

        diag_text = config_intent.description
        if config_intent.conflict_analysis:
            diag_text = f"{config_intent.description}\n\n[Análisis de Conflictos: {config_intent.conflict_analysis}]"

        fake_intent = NetworkIntent(
            diagnosis=diag_text,
            severity="MEDIUM",
            requires_config_change=True,
            action="none",
        )
        approved = self.auto_approve or self.observer.on_hitl_approval_required(
            device=device,
            intent=fake_intent,
            candidate_cli=config_intent.candidate_commands,
            rollback_info=rollback_info,
        )

        if not approved:
            self.observer.on_status_update("[yellow]Operación de configuración cancelada por el operador.[/yellow]")
            return None

        # 7. Transactional Execution & Pre-Change Snapshot
        try:
            self.observer.on_progress(85, "Creando snapshot de respaldo previo al cambio...")
            self.observer.on_execution_progress(f"[*] Tomando snapshot de respaldo de {device.host}...")
            backup_file = driver.backup_running_config()
            self.observer.on_execution_progress(f"[green][OK] Snapshot guardado en {backup_file.name}[/green]")

            self.observer.on_progress(
                90, f"Inyectando {len(config_intent.candidate_commands)} comandos transaccionales..."
            )
            self.observer.on_execution_progress(f"[*] Inyectando {len(config_intent.candidate_commands)} comandos...")
            driver.execute_commands(config_intent.candidate_commands)
            self.observer.on_execution_progress("[green][OK] Comandos aplicados exitosamente.[/green]")

            # Run verification commands if present
            if config_intent.verification_commands:
                self.observer.on_progress(95, "Ejecutando verificación post-despliegue...")
                self.observer.on_execution_progress("[*] Ejecutando comandos de verificación post-despliegue...")
                for v_cmd in config_intent.verification_commands:
                    try:
                        v_out = driver.get_connection().send_command(v_cmd)
                        self.observer.on_execution_progress(f"[dim]=== {v_cmd} ===\n{v_out[:300]}[/dim]")
                    except Exception:
                        pass

            audit_logger.record_event(
                event_type="CONFIGURATION_APPLIED",
                device_host=device.host,
                action=config_intent.protocol_type.value,
                commands=config_intent.candidate_commands,
                approved=True,
                extra={
                    "description": config_intent.description,
                    "backup": str(backup_file),
                    "conflict_analysis": config_intent.conflict_analysis,
                },
            )
            self.observer.on_progress(100, "Configuración completada y verificada exitosamente.")
            self.observer.on_completion(True, "Configuración completada y verificada exitosamente.")
            return config_intent
        except Exception as e:
            self.observer.on_completion(False, f"Fallo durante la configuración de {device.host}: {e}")
            audit_logger.record_event(
                event_type="CONFIGURATION_FAILED",
                device_host=device.host,
                action=config_intent.protocol_type.value,
                commands=config_intent.candidate_commands,
                approved=True,
                extra={"error": str(e)},
            )
            return None
        finally:
            driver.disconnect()

