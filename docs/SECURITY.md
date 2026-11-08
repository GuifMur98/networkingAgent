# 🛡️ Manual de Ciberseguridad y Modelo de Amenazas: NetworkingAgent Enterprise v2.1

> **Políticas de Hardening, Prevención de Inyecciones, Análisis Estático Pre-Flight y Protección de Infraestructura Crítica**

---

## 1. Resumen de Seguridad y Principios de Diseño

Los sistemas autónomos que administran elementos centrales de conectividad corporativa (routers BGP/OSPF, switches de centro de datos y gateways de acceso) operan en la intersección de dos vectores de riesgo críticos:
1. **Amenazas de Red y Automatización:** Inyecciones de comandos CLI, caídas accidentales de enlaces ascendentes (*uplinks*), borrado de configuraciones por plantillas defectuosas o desconexión por apagado de interfaces de gestión.
2. **Amenazas de Inteligencia Artificial:** Inyección indirecta de prompts (*Indirect Prompt Injection*) oculta en registros de syslog o paquetes de red, alucinaciones de comandos inexistentes o dañinos, y evasión de políticas de seguridad (*jailbreaks*).

Para mitigar estos riesgos de forma absoluta, **NetworkingAgent Enterprise v2.1** opera bajo el principio de **Defensa en Profundidad (*Defense-in-Depth*)**. Ningún componente confía ciegamente en otro, y el motor de IA está estructuralmente aislado de la ejecución en consola.

---

## 2. Matriz de Vectores de Amenaza y Mitigaciones v2.1

| Vector de Amenaza | Riesgo / Impacto Operativo | Severidad | Mitigación Implementada |
|---|---|:---:|---|
| **Comandos Destructivos en Automatización** | Un operador o script inyecta comandos de borrado (`erase`, `zeroize`, `format`, `reset-configuration`, `reload`). | 🔴 **CRÍTICO** | [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py) analiza estáticamente el script en modo dry-run y aborta el despliegue antes de abrir sockets SSH. |
| **Variables Jinja2 sin Renderizar** | Ejecución de scripts con variables huérfanas tipo `vlan {{ vlan_id }}` que provocan fallos de sintaxis en producción. | 🔴 **CRÍTICO** | Detección estática mediante `UNRENDERED_VARIABLE_PATTERN` con bloqueo inmediato de la ejecución. |
| **Indirect Prompt Injection** | Cargas de syslog o descripciones de síntomas diseñadas para manipular al LLM e inyectar usuarios no autorizados. | 🔴 **CRÍTICO** | Aislamiento XML `<telemetry_event>`, directivas estrictas en `HARDENED_SYSTEM_PROMPT` y bloqueo cognitivo (`severity="CRITICAL"`, `action="none"`). |
| **Aislamiento Accidental de Gestión** | El agente apaga o reinicia la interfaz que aloja la IP de conexión SSH o la ruta por defecto (`0.0.0.0/0`). | 🔴 **CRÍTICO** | Descubrimiento dinámico de IP de gestión (`discover_active_management_interfaces`) + bloqueo incondicional en [`BlastRadiusGuard`](../src/networking_agent/guardrails/blast_radius.py). |
| **CLI Command Injection & Metacaracteres** | Concatenación de sentencias shell mediante metacaracteres (`&&`, `;`, `\|`, `` ` ``, `$`). | 🔴 **CRÍTICO** | Expresiones regulares estrictas en Pydantic + validación en [`CommandValidator`](../src/networking_agent/guardrails/validator.py) previa a la conexión Netmiko. |
| **Inyección en Pruebas de Ping** | Ejecución de ping con hosts malformados (ej. `192.168.1.1; rm -rf /`). | 🔴 **CRÍTICO** | Validación estricta con Pydantic (`DeviceInventory.host`) y ejecución directa mediante `asyncio.create_subprocess_exec` sin invocar shell del SO (`shell=False`). |
| **Sintaxis Jerárquica Desbalanceada** | Scripts de Juniper Junos con llaves impares (`{` vs `}`) que dejan al dispositivo en estado inconsistente. | 🟠 **ALTO** | Balanceo aritmético de bloques en `ConfigSyntaxValidator` (`junos_brace_balance == 0`). |
| **Fuga de Credenciales de Equipos** | Contraseñas de acceso SSH expuestas en texto claro en logs o en disco. | 🟠 **ALTO** | Enmascaramiento con `SecretStr`, cifrado simétrico Fernet (AES-128-CBC) y permisos restrictivos `0600` en la base SQLite y en la llave maestra. |
| **Path Traversal en Backups** | Nombres de host o archivos maliciosos (ej. `../../etc/shadow`) para sobrescribir archivos arbitrarios. | 🟠 **ALTO** | Sanitización con regex alfanumérico + validación en disco mediante `backup_file.is_relative_to(backup_dir)`. |
| **Alteración de Auditoría** | Manipulación no autorizada de registros históricos de cambios. | 🟠 **ALTO** | Estructuración inmutable de eventos con hashes SHA-256 criptográficos y modo append-only en `audit.jsonl`. |
| **Agotamiento de Memoria (DoS)** | Payloads masivos de telemetría enviados al agente para saturar buffers de memoria o tokens de IA. | 🟡 **MEDIO** | Límite forzado a 30,000 caracteres en `TelemetryEvent` y purga de bytes nulos (`\x00`). |

---

## 3. Arquitectura Detallada de Guardarraíles

### 3.1. Validador de Sintaxis Pre-Flight (`ConfigSyntaxValidator`)

Antes de que un script manual, una plantilla Jinja2 o un conjunto de comandos generados por la IA sea enviado a la capa de red, es analizado por [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py).

#### 1. Detección de Patrones Destructivos y Shell Injections:
```python
FORBIDDEN_PATTERNS = [
    (re.compile(r"\b(reload|reboot|system\s+reboot)\b", re.IGNORECASE), "Comando de reinicio de equipo no permitido."),
    (
        re.compile(r"\b(format\s+flash:|erase\s+startup-config|write\s+erase)\b", re.IGNORECASE),
        "Comando destructivo de almacenamiento no permitido.",
    ),
    (
        re.compile(r"\b(request\s+system\s+zeroize|zeroize)\b", re.IGNORECASE),
        "Comando destructivo de borrado seguro (zeroize) bloqueado.",
    ),
    (
        re.compile(r"\b(/system\s+reset-configuration)\b", re.IGNORECASE),
        "Reset a valores de fábrica bloqueado en RouterOS.",
    ),
    (re.compile(r"[;&|`]", re.IGNORECASE), "Metacarácter de encadenamiento de comandos detectado."),
    (
        re.compile(r"\b(rm\s+-rf|nc\s+-e|/bin/sh|/bin/bash)\b", re.IGNORECASE),
        "Comando de ejecución de shell no permitido.",
    ),
]
```

#### 2. Detección de Variables Jinja2 sin Renderizar:
```python
UNRENDERED_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")
```
Si el operador olvidó sustituir una variable o si el motor de plantillas falló en procesar un parámetro, el análisis estático detecta la variable huérfana y genera un error fatal, evitando que el router reciba sintaxis no procesada.

#### 3. Verificaciones Específicas por Sistema Operativo:
- **Juniper Junos:** Calcula el balance algebraico de llaves `{` y `}`. Si `junos_brace_balance != 0`, el script es rechazado por inconsistencia estructural.
- **Cisco IOS / IOS-XE / NX-OS:** Verifica que las cadenas de texto con comillas dobles posean paridad numérica para evitar comandos cortados.
- **MikroTik RouterOS:** Alerta si una línea de configuración no comienza con el prefijo nativo `/` o `:` para prevenir rechazos del parser de RouterOS.

---

### 3.2. Blindaje de Blast Radius y Puertos WAN (`BlastRadiusGuard`)

La causa número uno de incidentes catastróficos en automatización de redes es la pérdida de gestión remota cuando una rutina apaga la interfaz a través de la cual el ingeniero está conectado.

1. **Descubrimiento Dinámico de Enlaces de Gestión:**  
   Al inicio de cada sesión de diagnóstico o remediación, [`discover_active_management_interfaces()`](../src/networking_agent/drivers/base.py) interroga dinámicamente las salidas de telemetría para ubicar qué interfaz física o virtual posee la IP de conexión SSH o la ruta por defecto (`0.0.0.0/0`).
2. **Regla de Blindaje Activo:**  
   [`BlastRadiusGuard`](../src/networking_agent/guardrails/blast_radius.py) prohíbe de forma terminante las acciones `restart_interface` y `disable_interface` sobre interfaces WAN, enlaces troncales o puertos de gestión (ej. `GigabitEthernet0/0/0`, `mgmt0`, `fxp0`, `ether1`, `sfp-sfpplus1`).
3. **Excepción de Diagnóstico Saludable:**  
   Si un síntoma reporta "internet lento", pero la interfaz WAN presenta 0 errores físicos y bajo tráfico, el guardarraíl bloquea cualquier intento de reinicio, identificando que el problema es de congestión externa y no de fallo de hardware local.

---

### 3.3. Filtro de Comandos a Nivel de Transporte (`CommandValidator`)

Directamente acoplado al método `execute_commands()` de todos los controladores de red:
- Bloquea creación o modificación de usuarios locales (`username`, `user add`, `password`, `secret`).
- Bloquea manipulación de autenticación centralizada (`radius`, `tacacs`).
- Bloquea herramientas de descarga o exfiltración (`tool fetch`, `tftp-server`, `guestshell`).
- Bloquea proxies no autorizados (`ip socks`, `ip proxy`).
- Bloquea tareas programadas persistentes no autorizadas (`system script`, `system scheduler`).

---

### 3.4. Bóveda Criptográfica y Almacenamiento Seguro

1. **Cifrado Simétrico Fernet:**
   - Implementado mediante la librería estándar de criptografía de Python (`cryptography.fernet`).
   - Basado en **AES-128 en modo CBC** con derivación de clave HMAC-SHA256 para autenticación de integridad.
2. **Clave Maestra Local (`data/.vault.key`):**
   - Se genera automáticamente con entropía criptográfica del sistema operativo.
   - En sistemas tipo POSIX (Linux/macOS), impone permisos estrictos de sólo lectura y escritura para el usuario propietario (`0600` / `stat.S_IRUSR | stat.S_IWUSR`).
3. **Base de Datos SQLite (`data/networking_agent.db`):**
   - Optimizada en modo WAL (`PRAGMA journal_mode = WAL;`) con permisos restrictivos `0600`.
   - Todas las credenciales de dispositivos y llaves de API (Gemini, OpenAI, Claude) se almacenan en columnas cifradas; la base de datos nunca almacena texto en claro.

---

### 3.5. Seguridad en Pruebas de Red y Paleta de Comandos

1. **Subprocesos Asíncronos Seguros:**
   - [`ConnectivityEngine`](../src/networking_agent/engine/connectivity.py) utiliza llamadas directas a subprocesos con arrays de argumentos (`["ping", "-n", "2", host]`), evitando terminantemente `shell=True` o concatenaciones de cadenas que permitan escapes shell.
2. **Restricción de Operaciones en la Paleta:**
   - [`NetworkAgentCommandProvider`](../src/networking_agent/tui/commands.py) expone exclusivamente acciones pre-mapeadas a métodos autorizados de la aplicación. No existe capacidad para ejecutar comandos shell arbitrarios a través de la paleta.
3. **Protección de la Bitácora de Auditoría:**
   - La funcionalidad de purga de pruebas valida explícitamente que los registros eliminados pertenezcan exclusivamente a sesiones sintéticas o de prueba, garantizando que el historial de despliegues en equipos de producción permanezca inalterable.

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

La suite de pruebas contiene tests automatizados diseñados específicamente para certificar la resistencia ante vectores de ataque:

```bash
uv run --no-sync pytest tests/test_guardrails.py tests/test_automation_module.py tests/test_crypto.py tests/test_models.py
```

### Casos Verificados en la Suite (172 pruebas):
- [x] Inyección de comandos shell con tuberías `|`, operadores `&&`, y punto y coma `;`.
- [x] Intentos de borrado de almacenamiento o reinicio (`write erase`, `zeroize`, `reset-configuration`).
- [x] Detección de variables Jinja2 huérfanas sin sustitución en plantillas de automatización.
- [x] Balanceo algebraico de llaves en bloques jerárquicos de Juniper Junos.
- [x] Detección de formatos sin prefijo obligatorio en MikroTik RouterOS.
- [x] Intentos de *Path Traversal* en nombres de host (`../../etc/passwd`).
- [x] Cargas de telemetría de gran tamaño (>30k caracteres) o con bytes nulos (`\x00`).
- [x] Aislamiento estricto de prompts manipulados dentro de etiquetas XML.
- [x] Cifrado y descifrado verificado con Fernet y permisos de archivo `0600`.
- [x] Pruebas de conectividad con hosts no válidos o maliciosos rechazadas de forma segura.
