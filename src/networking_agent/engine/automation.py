"""Template rendering, pre-flight syntax dry-run, and transactional multi-device batch deployment."""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import jinja2

from networking_agent.core.audit import audit_logger
from networking_agent.core.db import db
from networking_agent.core.logging import logger
from networking_agent.drivers.factory import get_os_driver
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.config_intent import AutomationTemplate, BatchDeploymentResult
from networking_agent.models.device import DeviceInventory

BUILTIN_TEMPLATES: List[AutomationTemplate] = [
    AutomationTemplate(
        name="Cisco IOS: Hardening Base y Seguridad",
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
        name="Cisco IOS: Aprovisionamiento de VLAN y SVI",
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
        name="Cisco IOS: Enrutamiento OSPF Área 0",
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
        name="Cisco IOS: Servicios NTP y Syslog Corporativo",
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
        name="Cisco NX-OS: Features y OSPF Área 0",
        vendor_family="cisco_nxos",
        description="Activación de feature OSPF y configuración de proceso backbone en Nexus.",
        template_content="""feature ospf
router ospf {{ process_id }}
 router-id {{ router_id }}
exit
interface {{ routed_interface }}
 ip router ospf {{ process_id }} area 0.0.0.0
 no shutdown
exit
""",
        parameters_schema={
            "process_id": "1",
            "router_id": "10.255.255.1",
            "routed_interface": "Ethernet1/1",
        },
    ),
    AutomationTemplate(
        name="Cisco NX-OS: Trunking 802.1Q y Port-Channel LACP",
        vendor_family="cisco_nxos",
        description="Agregación de enlaces LACP con trunk dot1q para conmutadores Nexus.",
        template_content="""feature lacp
interface port-channel {{ channel_id }}
 switchport
 switchport mode trunk
 switchport trunk allowed vlan {{ allowed_vlans }}
 no shutdown
exit
""",
        parameters_schema={
            "channel_id": "10",
            "allowed_vlans": "10,20,30,100",
        },
    ),
    AutomationTemplate(
        name="Juniper Junos: Creación de VLAN e Interfaz IRB",
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
    AutomationTemplate(
        name="Juniper Junos: Enrutamiento OSPFv2 Jerárquico",
        vendor_family="juniper_junos",
        description="Activación de proceso OSPFv2 en área 0 con interfaces enrutadas en Junos.",
        template_content="""set routing-options router-id {{ router_id }}
set protocols ospf area 0.0.0.0 interface {{ uplink_interface }} priority 100
set protocols ospf area 0.0.0.0 interface lo0.0 passive
""",
        parameters_schema={
            "router_id": "172.16.0.1",
            "uplink_interface": "ge-0/0/0.0",
        },
    ),
    AutomationTemplate(
        name="MikroTik RouterOS v7: VLAN Trunk y Bridge Filtering",
        vendor_family="mikrotik_routeros",
        description="Aprovisionamiento de VLANs y filtrado L2 seguro en bridge de RouterOS v7.",
        template_content="""/interface bridge vlan
add bridge={{ bridge_name }} tagged={{ trunk_port }} vlan-ids={{ vlan_id }}
/interface vlan add name=vlan{{ vlan_id }} interface={{ bridge_name }} vlan-id={{ vlan_id }}
/ip address add address={{ ip_cidr }} interface=vlan{{ vlan_id }}
""",
        parameters_schema={
            "bridge_name": "bridge1",
            "trunk_port": "ether1",
            "vlan_id": "50",
            "ip_cidr": "192.168.50.1/24",
        },
    ),
    AutomationTemplate(
        name="MikroTik RouterOS v7: Instancia OSPFv2 / v3",
        vendor_family="mikrotik_routeros",
        description="Configuración de instancia y área OSPF moderna en RouterOS v7.",
        template_content="""/routing ospf instance add name={{ instance_name }} router-id={{ router_id }}
/routing ospf area add name=backbone instance={{ instance_name }} area-id=0.0.0.0
/routing ospf interface-template add area=backbone interfaces={{ interface_name }}
""",
        parameters_schema={
            "instance_name": "ospf-main",
            "router_id": "192.168.88.1",
            "interface_name": "ether1",
        },
    ),
]


class TemplateEngine:
    """Renderer and catalog manager for configuration templates."""

    VARIABLE_REGEX = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")

    @classmethod
    def get_templates(cls) -> List[AutomationTemplate]:
        """Returns the available catalog of configuration templates.

        Synchronizes builtin templates into SQLite storage if missing, and loads
        all saved templates (both built-in and user-created).
        """
        try:
            stored = db.list_templates()
            if not stored:
                # Seed builtin templates into DB
                for tpl in BUILTIN_TEMPLATES:
                    db.save_template(
                        name=tpl.name,
                        vendor_family=tpl.vendor_family,
                        description=tpl.description,
                        template_content=tpl.template_content,
                        parameters_schema=tpl.parameters_schema,
                        is_builtin=True,
                    )
                return list(BUILTIN_TEMPLATES)

            # Return list from DB
            result: List[AutomationTemplate] = []
            seen_names = set()
            for r in stored:
                seen_names.add(r["name"])
                result.append(
                    AutomationTemplate(
                        name=r["name"],
                        vendor_family=r.get("vendor_family", "cisco_ios"),
                        description=r.get("description", ""),
                        template_content=r.get("template_content", ""),
                        parameters_schema=r.get("parameters_schema", {}),
                    )
                )

            # Guarantee any missing builtin templates are included
            for b_tpl in BUILTIN_TEMPLATES:
                if b_tpl.name not in seen_names:
                    result.append(b_tpl)
                    db.save_template(
                        name=b_tpl.name,
                        vendor_family=b_tpl.vendor_family,
                        description=b_tpl.description,
                        template_content=b_tpl.template_content,
                        parameters_schema=b_tpl.parameters_schema,
                        is_builtin=True,
                    )

            return result
        except Exception as e:
            logger.warning(f"Error loading templates from DB, using fallback builtin list: {e}")
            return list(BUILTIN_TEMPLATES)

    @classmethod
    def extract_variables(cls, template_content: str) -> List[str]:
        """Extracts unique variable names from {{ variable }} tokens in template content."""
        if not template_content:
            return []
        matches = cls.VARIABLE_REGEX.findall(template_content)
        return sorted(list(set(matches)))

    @classmethod
    def save_custom_template(
        cls,
        name: str,
        vendor_family: str,
        description: str,
        template_content: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> AutomationTemplate:
        """Stores a new or updated template into SQLite storage."""
        schema = parameters_schema or {}
        if not schema:
            vars_found = cls.extract_variables(template_content)
            schema = {var_name: "" for var_name in vars_found}

        db.save_template(
            name=name,
            vendor_family=vendor_family,
            description=description,
            template_content=template_content,
            parameters_schema=schema,
            is_builtin=False,
        )

        return AutomationTemplate(
            name=name,
            vendor_family=vendor_family,
            description=description,
            template_content=template_content,
            parameters_schema=schema,
        )

    @classmethod
    def delete_custom_template(cls, name: str) -> bool:
        """Removes a custom template from storage."""
        return db.delete_template_by_name(name)

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

    def _notify_progress(self, percent: float, step: str) -> None:
        if self.observer and hasattr(self.observer, "update_progress"):
            try:
                self.observer.update_progress(percent, step)
            except Exception as e:
                logger.debug(f"Observer update_progress failed: {e}")

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

        self._notify_progress(10.0, "Validando sintaxis y guardarraíles pre-vuelo...")

        # 1. Pre-flight static syntax validation
        validation = ConfigSyntaxValidator.validate_script(raw_script, vendor_family=vendor_family)
        if not validation.is_valid:
            error_details = " | ".join(validation.errors)
            self._notify(f"[bold red][!] Despliegue cancelado: Errores de validación sintáctica: {error_details}[/]")
            self._notify_progress(100.0, "Despliegue cancelado por error sintáctico.")
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
        self._notify_progress(20.0, f"Conectando a {len(devices)} equipos destino...")

        successful_count = 0
        failed_count = 0
        total_devices = len(devices)

        for idx, device in enumerate(devices):
            dev_pct_base = 25.0 + (idx / total_devices) * 70.0
            self._notify_progress(
                dev_pct_base,
                f"[{idx+1}/{total_devices}] Conectando a {device.host} ({device.device_type})...",
            )
            self._notify(f"[*] Conectando a {device.host} ({device.device_type})...")
            driver = get_os_driver(device)
            backup_path = None

            try:
                # Pre-change snapshot backup
                self._notify_progress(
                    dev_pct_base + 5.0,
                    f"[{idx+1}/{total_devices}] Creando snapshot de seguridad en {device.host}...",
                )
                backup_path = driver.backup_running_config()
                self._notify(f"[green][OK] Snapshot de respaldo guardado en {backup_path.name}[/]")

                # Execute configuration set
                self._notify_progress(
                    dev_pct_base + 12.0,
                    f"[{idx+1}/{total_devices}] Aplicando configuración en {device.host}...",
                )
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
                self._notify_progress(
                    dev_pct_base + 12.0,
                    f"[{idx+1}/{total_devices}] Reversión de emergencia en {device.host}...",
                )
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

        self._notify_progress(100.0, "Despliegue en lote finalizado.")
        summary = f"Lote {job_id} finalizado: {successful_count}/{len(devices)} exitosos, {failed_count} fallidos."
        self._notify(f"[bold green]{summary}[/bold green]")

        return BatchDeploymentResult(
            job_id=job_id,
            timestamp=timestamp,
            target_hosts=target_hosts,
            device_results=device_results,
            summary=summary,
        )
