# 🛡️ Manual de Ciberseguridad y Modelo de Amenazas: NetworkingAgent Enterprise v2.1.1

> **Políticas de Hardening, Prevención de Inyecciones (SSTI/CLI), Análisis Estático Pre-Flight, Transporte SSH MitM-Proof y Criptografía Forense**

---

## 1. Resumen de Seguridad y Principios de Diseño

Los sistemas autónomos que administran elementos centrales de conectividad corporativa (routers BGP/OSPF, switches de centro de datos y gateways de acceso) operan en la intersección de vectores de riesgo de infraestructura e inteligencia artificial:
1. **Amenazas de Red y Automatización:** Inyecciones de plantillas Jinja2 (SSTI), ataques Man-in-the-Middle (MitM) en el transporte SSH, inyecciones de comandos CLI, caídas accidentales de enlaces ascendentes (*uplinks*), borrado de configuraciones o desconexión por apagado de interfaces de gestión.
2. **Amenazas de Inteligencia Artificial:** Inyección indirecta de prompts (*Indirect Prompt Injection*) oculta en registros de syslog o paquetes de red, alucinaciones de comandos inexistentes o dañinos, y evasión de políticas de seguridad (*jailbreaks*).
3. **Amenazas de Sistema Operativo Local:** Secuestro de directorio de trabajo (*CWD Hijacking*), filtración de credenciales en bitácoras de auditoría, permisos laxos en archivos de claves maestras y ejecución ciega de scripts web en instaladores.

Para mitigar estos riesgos de forma absoluta, **NetworkingAgent Enterprise v2.1.1** opera bajo el principio de **Defensa en Profundidad (*Defense-in-Depth*)**. Ningún componente confía ciegamente en otro, y el motor de IA está estructuralmente aislado de la ejecución en consola.

---

## 2. Matriz Consolidada de Vectores de Amenaza y Mitigaciones v2.1.1

| Vector de Amenaza / Vulnerabilidad | Riesgo / Impacto Operativo | Severidad | Mitigación Implementada |
|---|---|:---:|---|
| **Server-Side Template Injection (SSTI) en Jinja2** | Ejecución remota o local de código (RCE) mediante introspección de objetos Python (`__class__`, `__mro__`, `__globals__`). | 🔴 **CRÍTICO** | [`HardenedSandboxedEnvironment`](../src/networking_agent/engine/automation.py) bloquea terminantemente el acceso a atributos dunder, callables inseguros (`eval`, `popen`, etc.) y previene escapes del sandbox. |
| **Aceptación Ciega de Llaves SSH (Riesgo MitM)** | Intercepción de sesiones SSH y credenciales administrativas por spoofing de router o envenenamiento ARP/DNS. | 🔴 **CRÍTICO** | Carga obligatoria de `known_hosts` del sistema (`system_host_keys=True`), soporte para `ssh_strict` y detección de discrepancia de llaves (`BadHostKeyException`). |
| **Comandos Destructivos y Backdoors en Red** | Scripts o plantillas que inyectan reinicios, borrado de configs, backdoors SNMP RW, degradación a Telnet o secuestro de rutas. | 🔴 **CRÍTICO** | [`CommandValidator`](../src/networking_agent/guardrails/validator.py) y [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py) con listas negras ampliadas que vetan copias remotas, SNMP RW, Telnet y default routes no autorizadas. |
| **Aislamiento Accidental de Gestión** | El agente apaga o reinicia la interfaz que aloja la IP de conexión SSH o la ruta por defecto (`0.0.0.0/0`). | 🔴 **CRÍTICO** | Descubrimiento dinámico de IP de gestión (`discover_active_management_interfaces`) + bloqueo incondicional en [`BlastRadiusGuard`](../src/networking_agent/guardrails/blast_radius.py). |
| **Indirect Prompt Injection** | Cargas de syslog o descripciones de síntomas diseñadas para manipular al LLM e inyectar comandos o usuarios. | 🔴 **CRÍTICO** | Aislamiento XML `<telemetry_event>`, directivas estrictas en `HARDENED_SYSTEM_PROMPT` y bloqueo cognitivo (`severity="CRITICAL"`, `action="none"`). |
| **Inyección en Pruebas de Ping** | Ejecución de ping con hosts malformados (ej. `192.168.1.1; rm -rf /`). | 🔴 **CRÍTICO** | Validación estricta con Pydantic (`DeviceInventory.host`) y ejecución directa mediante `asyncio.create_subprocess_exec` sin invocar shell del SO (`shell=False`). |
| **Permisos Ineficaces en Llave Maestra** | Herencia de permisos de lectura de la clave Fernet para usuarios locales bajo Windows NTFS. | 🟠 **ALTO** | En Windows, [`secure_file_permissions`](../src/networking_agent/core/crypto.py) elimina herencia y restringe acceso exclusivamente al usuario actual mediante `icacls /inheritance:r /grant:r "%USERNAME%:(F)"`. En POSIX aplica `0600`. |
| **Confusión de Directorio (CWD Hijacking)** | Carga de base de datos o clave criptográfica adulterada al ejecutar `networking-agent` desde carpetas arbitrarias. | 🟠 **ALTO** | Rutas ancladas mediante [`get_app_data_dir()`](../src/networking_agent/core/config.py) con prioridad de entorno `NETWORKING_AGENT_DATA_DIR` y resolución a `%LOCALAPPDATA%\NetworkingAgent\data`. |
| **Fuga de Credenciales en Auditoría** | Persistencia de contraseñas, secretos, comunidades SNMP o pre-shared keys en texto plano en `audit.jsonl`. | 🟡 **MEDIO** | Filtrado universal con [`mask_sensitive_data()`](../src/networking_agent/core/logging.py) aplicado a todos los comandos y salidas antes de persistir en auditoría. |
| **Manipulación no Detectada de Auditoría** | Falsificación o borrado inadvertido de registros históricos de operaciones de red. | 🟡 **MEDIO** | Encadenamiento criptográfico **SHA-256** continuo (`prev_hash` + `event_hash`) en cada evento de [`AuditLogger`](../src/networking_agent/core/audit.py) con función de verificación `verify_audit_integrity()`. |
| **Ejecución Ciega en Instaladores** | Instalación mediante tuberías ciegas a shell (`curl | sh` o `irm | iex`). | 🟡 **MEDIO** | Descarga segura a archivos temporales aislados, validación de tamaño e integridad antes de la ejecución local y purga inmediata tras finalizar. |

---

## 3. Arquitectura Detallada de Guardarraíles y Controles

### 3.1. Sandbox Estricto de Plantillas (`HardenedSandboxedEnvironment`)

Para neutralizar de forma definitiva la ejecución remota de código por inyección de plantillas (SSTI), el motor [`TemplateEngine`](../src/networking_agent/engine/automation.py) encapsula el renderizado dentro de un entorno Jinja2 restringido:
- **Inspección de Atributos:** Se prohíbe el acceso a cualquier atributo que comience con guión bajo `_` o atributos de introspección de runtime (`__class__`, `__mro__`, `__globals__`, `f_globals`, `f_builtins`, etc.).
- **Inspección de Callables:** Se prohíbe la invocación de funciones de sistema (`eval`, `exec`, `open`, `__import__`, `system`, `popen`, `spawn`, `compile`, etc.).
- **Interrupción Inmediata:** Cualquier intento de evasión lanza `TemplateSecurityError` y se registra una alerta crítica de auditoría.

```python
class HardenedSandboxedEnvironment(SandboxedEnvironment):
    def is_safe_attribute(self, obj: Any, attr: str, value: Any) -> bool:
        if attr.startswith("_") or attr in ("format", "format_map", "mro", "gi_frame", "f_globals", "f_builtins"):
            return False
        return super().is_safe_attribute(obj, attr, value)
```

---

### 3.2. Seguridad en el Transporte SSH y Mitigación de MitM

La comunicación con los equipos de red a través de Netmiko / Paramiko se endurece para evitar ataques de suplantación de identidad o intercepción de credenciales:
1. **Validación de Llaves Públicas:** `to_netmiko_dict()` activa por defecto `system_host_keys=True`, cargando el almacén `known_hosts` del sistema.
2. **Detección de Discrepancias:** Si la llave pública del router difiere de la registrada previamente, Paramiko lanza `BadHostKeyException`. El controlador captura la excepción y emite una alerta crítica de seguridad (`ALERTA CRITICA DE SEGURIDAD (MitM detectado)`), abortando la conexión antes de transmitir credenciales.
3. **Modo Estricto Opcional:** Se proporciona soporte para `ssh_strict=True` y archivos `known_hosts` alternativos mediante `alt_host_keys` y `alt_key_file`.

---

### 3.3. Filtro de Comandos a Nivel de Transporte y Sintaxis Pre-Flight

Tanto [`CommandValidator`](../src/networking_agent/guardrails/validator.py) como [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py) vetan de forma determinista:
- **Destrucción y Reinicio:** `reload`, `reboot`, `format flash:`, `erase startup-config`, `zeroize`, `reset-configuration`.
- **Cuentas y Credenciales:** Creación de usuarios (`username`, `user add`), modificación de contraseñas locales o agentes AAA (`radius`, `tacacs`).
- **Comunidades SNMP RW:** Declaraciones de comunidades con permisos de escritura (`snmp-server community <nombre> RW`).
- **Descargas no Autorizadas y Backdoors:** `copy tftp:`, `copy ftp:`, `copy http:`, `tool fetch`, `tftp-server`, `guestshell`, `start shell`.
- **Protocolos en Texto Claro:** Degradación de transporte vty a Telnet (`transport input telnet`, `transport input all`).
- **Almacenamiento Inseguro:** Desactivación de cifrado de contraseñas (`no service password-encryption`).
- **Desvío de Tráfico:** Inyecciones no autorizadas de rutas por defecto (`ip route 0.0.0.0 0.0.0.0`).

---

### 3.4. Bóveda Criptográfica, ACLs de Sistema Operativo y Aislamiento CWD

1. **Cifrado Simétrico Fernet (AES-128-CBC + HMAC-SHA256):**
   - Utilizado para proteger todas las credenciales locales de routers y claves API de IA almacenadas en la base de datos SQLite.
2. **Restricción de DACLs en Windows (`icacls`):**
   - La clave maestra `.vault.key` aplica permisos estrictos. En sistemas Windows, se deshabilita la herencia de permisos NTFS y se otorga control total exclusivamente al usuario actual:
     `icacls "<path>" /inheritance:r /grant:r "%USERNAME%:(F)"`
   - En sistemas tipo POSIX (Linux/macOS), se aplican permisos `0600` (`stat.S_IRUSR | stat.S_IWUSR`).
3. **Protección contra CWD Hijacking:**
   - La resolución de rutas de almacenamiento (`get_app_data_dir()` y `get_app_log_dir()`) prioriza la variable de entorno `NETWORKING_AGENT_DATA_DIR` o se ancla de forma absoluta en `%LOCALAPPDATA%\NetworkingAgent\data`.
   - Los lanzadores ejecutables (`networking-agent.cmd` y `networking-agent`) cambian de directorio automáticamente a la carpeta de instalación de la aplicación antes de invocar Python.

---

### 3.5. Encadenamiento Criptográfico SHA-256 en Auditoría y Sanitización

1. **Sanitización de Secretos (`mask_sensitive_data`):**
   - Antes de escribir cualquier evento en `logs/audit.jsonl`, todos los comandos CLI y salidas de ejecución se procesan para enmascarar contraseñas, secretos de enable, comunidades SNMP y tokens Bearer con secuencias `********`.
2. **Encadenamiento Criptográfico SHA-256:**
   - Cada evento incluye el hash del evento anterior (`prev_hash`) y su propio hash canónico (`event_hash`).
   - El primer registro inicia con `GENESIS_0000000000000000000000000000000000000000000000000000000000000000`.
   - La función `verify_audit_integrity()` permite a auditores y operadores verificar la inmutabilidad de la cadena y detectar cualquier línea adulterada o borrada.
3. **Respaldo Previo a la Purga de Pruebas:**
   - Cuando un operador solicita la purga de registros sintéticos en la TUI, se genera una copia forense automática en `logs/audit_backup_pre_purge.jsonl` antes de guardar los registros auténticos.

---

## 4. Compuerta de Aprobación Humana (Human-in-the-Loop)

Por política de diseño, **ningún cambio en configuración o remediación se ejecuta sin la confirmación explícita de un operador humano**, a menos que se active intencionalmente el modo de pruebas desatendidas (`--auto-approve`).

La ventana modal de aprobación presenta de manera inmutable:
- Nombre y dirección IP del dispositivo destino.
- Diagnóstico técnico y nivel de severidad asignado por la IA.
- **Previsualización exacta de comandos CLI nativos a inyectar.**
- Mecanismo de reversión y rollback garantizado en caso de fallo.
- Atajos de confirmación rápida: `Y` para autorizar y `N` para cancelar y auditar el rechazo.

---

## 5. Pruebas Automatizadas de Seguridad

La suite de pruebas contiene **194 pruebas automatizadas (100% passing)**, incluyendo tests diseñados específicamente para certificar la resistencia ante vectores de ataque:

```bash
uv run --no-sync pytest tests/
```

### Casos Verificados en la Suite:
- [x] Bloqueo de Server-Side Template Injection (SSTI) y fugas por introspección en `TemplateEngine`.
- [x] Detección de ataques Man-in-the-Middle y validación de llaves públicas SSH en Netmiko.
- [x] Bloqueo de comandos destructivos, copias TFTP, comunidades SNMP RW, Telnet y desvíos de ruta por defecto.
- [x] Aplicación de permisos estrictos en Windows (`icacls`) y POSIX (`0600`) para la llave criptográfica.
- [x] Aislamiento de rutas de datos contra secuestro de directorio de trabajo (CWD Hijacking).
- [x] Enmascaramiento de contraseñas, secretos y tokens en el registro de auditoría forense.
- [x] Encadenamiento criptográfico continuo SHA-256 y detección matemática de adulteración en `audit.jsonl`.
- [x] Descargas seguras en instaladores con eliminación de tuberías directas a shell (`curl | sh` / `irm | iex`).
