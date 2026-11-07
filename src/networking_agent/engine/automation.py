"""Template rendering, pre-flight syntax dry-run, and transactional multi-device batch deployment."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import jinja2

from networking_agent.core.audit import audit_logger
from networking_agent.core.logging import logger
from networking_agent.drivers.factory import get_os_driver
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.config_intent import AutomationTemplate, BatchDeploymentResult
from networking_agent.models.device import DeviceInventory

BUILTIN_TEMPLATES: List[AutomationTemplate] = [
    AutomationTemplate(
        name="Hardening Base y Seguridad",
        vendor_family="cisco_ios",
        description="Aseguramiento de servicios, timeouts de sesión SSH y cifrado de contraseñas locales.",
        template_content="""! Baseline de Hardening Cisco IOS/XE
service password-encryption
no ip http server
no ip http secure-server
no ip source-route
line vty 0 4
 transport input ssh
 exec-timeout 10 0
 login local
exit
""",
        parameters_schema={},
    ),
    AutomationTemplate(
        name="Aprovisionamiento de VLAN y SVI",
        vendor_family="cisco_ios",
        description="Creación de VLAN de datos con interfaz virtual conmutada (SVI) y descripción.",
        template_content="""! Plantilla de VLAN con SVI
vlan {{ vlan_id }}
 name {{ vlan_name }}
exit
interface Vlan{{ vlan_id }}
 description {{ vlan_description }}
 ip address {{ ip_address }} {{ netmask }}
 no shutdown
exit
""",
        parameters_schema={
            "vlan_id": "100",
            "vlan_name": "VENTAS",
            "vlan_description": "Subred de Usuarios Ventas",
            "ip_address": "192.168.100.1",
            "netmask": "255.255.255.0",
        },
    ),
    AutomationTemplate(
        name="Enrutamiento OSPF Área 0",
        vendor_family="cisco_ios",
        description="Activación de proceso OSPF monorárea con Router-ID y declaración de red.",
        template_content="""! Plantilla OSPF Backbone
router ospf {{ process_id }}
 router-id {{ router_id }}
 network {{ network_cidr }} area 0
 passive-interface default
 no passive-interface {{ uplink_interface }}
exit
""",
        parameters_schema={
            "process_id": "1",
            "router_id": "1.1.1.1",
            "network_cidr": "10.0.0.0 0.255.255.255",
            "uplink_interface": "GigabitEthernet0/1",
        },
    ),
    AutomationTemplate(
        name="Servicios NTP y Syslog Corporativo",
        vendor_family="cisco_ios",
        description="Sincronización de reloj NTP y reenvío de logs a servidor central SIEM/Syslog.",
        template_content="""! Configuración de Gestión y Telemetría
ntp server {{ ntp_server }}
logging host {{ syslog_server }}
logging trap warnings
service timestamps log datetime msec localtime show-timezone
""",
        parameters_schema={
            "ntp_server": "10.10.10.123",
            "syslog_server": "10.10.10.514",
        },
    ),
    AutomationTemplate(
        name="Junos: Creación de VLAN e Interfaz IRB",
        vendor_family="juniper_junos",
        description="Definición de VLAN 802.1Q con interfaz integrada de enrutamiento IRB en Junos.",
        template_content="""set vlans {{ vlan_name }} vlan-id {{ vlan_id }}
set vlans {{ vlan_name }} l3-interface irb.{{ vlan_id }}
set interfaces irb unit {{ vlan_id }} family inet address {{ ip_cidr }}
""",
        parameters_schema={
            "vlan_name": "CORP-DATA",
            "vlan_id": "20",
            "ip_cidr": "172.16.20.1/24",
        },
    ),
]


class TemplateEngine:
    """Renderer and catalog manager for configuration templates."""

    @classmethod
    def get_templates(cls) -> List[AutomationTemplate]:
        """Returns the available catalog of configuration templates."""
        return list(BUILTIN_TEMPLATES)

    @classmethod
    def render(cls, template_content: str, variables: Dict[str, Any]) -> str:
        """Renders a template string using Jinja2 with provided parameter dictionary."""
        template = jinja2.Template(template_content, undefined=jinja2.StrictUndefined)
        return template.render(**variables)


class BatchDeployer:
    """Orchestrates transactional batch configuration across multiple inventory devices."""

    def __init__(self, observer: Optional[Any] = None):
        self.observer = observer

    def _notify(self, message: str) -> None:
        if self.observer and hasattr(self.observer, "append_log"):
            self.observer.append_log(message)
        logger.info(message)

    def deploy_to_devices(
        self,
        devices: List[DeviceInventory],
        raw_script: str,
        vendor_family: str = "cisco_ios",
    ) -> BatchDeploymentResult:
        """Executes a multi-device deployment job with per-device pre-snapshot and rollback.

        Args:
            devices: Selected target devices to configure.
            raw_script: Configuration text to inject onto each device.
            vendor_family: Vendor OS family for syntax checking.

        Returns:
            BatchDeploymentResult with detailed per-device logs and status.
        """
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc)
        target_hosts = [d.host for d in devices]
        device_results: Dict[str, Dict[str, Any]] = {}

        # 1. Pre-flight static syntax validation
        validation = ConfigSyntaxValidator.validate_script(raw_script, vendor_family=vendor_family)
        if not validation.is_valid:
            error_details = " | ".join(validation.errors)
            self._notify(f"[bold red][!] Despliegue cancelado: Errores de validación sintáctica: {error_details}[/]")
            return BatchDeploymentResult(
                job_id=job_id,
                timestamp=timestamp,
                target_hosts=target_hosts,
                device_results={h: {"success": False, "error": error_details} for h in target_hosts},
                summary=f"Despliegue cancelado por error sintáctico: {error_details}",
            )

        commands_to_apply = validation.clean_commands
        self._notify(
            f"[bold cyan][>] Iniciando lote {job_id}: {len(commands_to_apply)} comandos en {len(devices)} equipos...[/]"
        )

        successful_count = 0
        failed_count = 0

        for device in devices:
            self._notify(f"[*] Conectando a {device.host} ({device.device_type})...")
            driver = get_os_driver(device)
            backup_path = None

            try:
                # Pre-change snapshot backup
                backup_path = driver.backup_running_config()
                self._notify(f"[green][OK] Snapshot de respaldo guardado en {backup_path.name}[/]")

                # Execute configuration set
                output = driver.execute_commands(commands_to_apply)
                self._notify(f"[green][OK] Comandos inyectados exitosamente en {device.host}[/]")

                device_results[device.host] = {
                    "success": True,
                    "applied_commands": commands_to_apply,
                    "output": output,
                    "backup": str(backup_path),
                    "rollback_applied": False,
                }
                successful_count += 1

                audit_logger.record_event(
                    event_type="BATCH_DEPLOYMENT_SUCCESS",
                    device_host=device.host,
                    action="configuration_batch",
                    commands=commands_to_apply,
                    approved=True,
                    extra={"job_id": job_id, "backup": str(backup_path)},
                )

            except Exception as e:
                failed_count += 1
                self._notify(f"[bold red][!] Error en {device.host}: {e}. Iniciando reversión...[/]")
                rollback_ok = False
                if backup_path and backup_path.exists():
                    try:
                        rollback_ok = driver.rollback(backup_path)
                        self._notify(f"[yellow]Rollback ejecutado en {device.host}: {rollback_ok}[/]")
                    except Exception as rb_err:
                        self._notify(f"[bold red]Fallo crítico al revertir {device.host}: {rb_err}[/]")

                device_results[device.host] = {
                    "success": False,
                    "applied_commands": commands_to_apply,
                    "error": str(e),
                    "backup": str(backup_path) if backup_path else None,
                    "rollback_applied": rollback_ok,
                }

                audit_logger.record_event(
                    event_type="BATCH_DEPLOYMENT_FAILURE",
                    device_host=device.host,
                    action="configuration_batch",
                    commands=commands_to_apply,
                    approved=True,
                    extra={"job_id": job_id, "error": str(e), "rollback_applied": rollback_ok},
                )
            finally:
                driver.disconnect()

        summary = f"Lote {job_id} finalizado: {successful_count}/{len(devices)} exitosos, {failed_count} fallidos."
        self._notify(f"[bold green]{summary}[/bold green]")

        return BatchDeploymentResult(
            job_id=job_id,
            timestamp=timestamp,
            target_hosts=target_hosts,
            device_results=device_results,
            summary=summary,
        )
