# 📖 Guía Completa de Uso y Operación: NetworkingAgent Enterprise

Bienvenido a la guía oficial de usuario y operaciones para **NetworkingAgent**, el asistente autónomo de ingeniería de redes con automatización en bucle cerrado (*Closed-Loop Automation*) e inteligencia artificial multi-cerebro.

---

## 📑 Tabla de Contenidos

1. [Requisitos Previos y Entorno](#1-requisitos-previos-y-entorno)
2. [Instalación Rápida](#2-instalación-rápida)
3. [Configuración Inicial y Bóveda Criptográfica](#3-configuración-inicial-y-bóveda-criptográfica)
4. [Gestión de Inventario de Dispositivos](#4-gestión-de-inventario-de-dispositivos)
5. [Modos de Operación](#5-modos-de-operación)
   - [Modo Proactivo (Diagnóstico por Síntomas)](#51-modo-proactivo-diagnóstico-por-síntomas)
   - [Modo Reactivo (Ingesta de Telemetría / Syslog)](#52-modo-reactivo-ingesta-de-telemetría--syslog)
6. [Flujo Interactivo Human-in-the-Loop (HitL)](#6-flujo-interactivo-human-in-the-loop-hitl)
7. [Guardarraíles de Seguridad y Blast Radius](#7-guardarraíles-de-seguridad-y-blast-radius)
8. [Verificación Post-Cambio y Rollback Autónomo](#8-verificación-post-cambio-y-rollback-autónomo)
9. [Auditoría y Trazabilidad](#9-auditoría-y-trazabilidad)
10. [Solución de Problemas Frecuentes (FAQ)](#10-solución-de-problemas-frecuentes-faq)

---

## 1. Requisitos Previos y Entorno

- **Sistema Operativo:** Linux, macOS o Windows (PowerShell / WSL).
- **Python:** Versión `>= 3.12` (Recomendado: Python `3.14`).
- **Gestor de Paquetes:** [`uv`](https://github.com/astral-sh/uv) (Recomendado para resolución determinista e instantánea).
- **Conectividad de Red:** Acceso TCP/22 (SSH) hacia los routers o switches gestionados.
- **Cerebro de IA:**
  - **Opción Local / Privada:** [Ollama](https://ollama.com/) corriendo localmente con el modelo `netexpert:latest` o `llama3.1`.
  - **Opción Cloud:** API Key de **Google Gemini** (`gemini-2.5-pro` o `gemini-2.5-flash`), **OpenAI**, o **Anthropic**.

---

## 2. Instalación Rápida

Utilizando `uv` (recomendado):

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd networkingAgent

# 2. Sincronizar el entorno virtual y dependencias de producción y desarrollo
uv sync --extra dev

# 3. Verificar que la suite de pruebas se ejecute al 100%
uv run --no-sync pytest
```

---

## 3. Configuración Inicial y Bóveda Criptográfica

NetworkingAgent implementa almacenamiento persistente en **SQLite** (`data/networking_agent.db`) cifrado mediante la clave simétrica local `data/.vault.key` (con permisos `0600`).

### 3.1. Plantilla de Variables de Entorno (`.env`)

Copia la plantilla `.env.example`:

```bash
cp .env.example .env
```

Variables disponibles:

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `AI_PROVIDER` | Proveedor cerebral activo (`ollama`, `gemini`, `openai`, `anthropic`) | `ollama` |
| `AI_MODEL` | Modelo específico a invocar | `netexpert:latest` |
| `OLLAMA_HOST` | Endpoint de la API local de Ollama | `http://localhost:11434` |
| `GEMINI_API_KEY` | Llave de API para Google Gemini | `None` |
| `OPENAI_API_KEY` | Llave de API para OpenAI | `None` |
| `ANTHROPIC_API_KEY` | Llave de API para Anthropic Claude | `None` |
| `ENFORCE_GUARDRAILS` | Bloqueo activo de inyecciones y blast radius | `true` |
| `AUTO_ROLLBACK_ON_FAILURE` | Reversión automática si falla la verificación | `true` |
| `SSH_TIMEOUT` | Timeout en segundos para transacciones Netmiko | `30` |

### 3.2. Modos de Lanzamiento: TUI vs CLI

NetworkingAgent soporta una arquitectura dual desacoplada:

1. **Interfaz Gráfica de Terminal Reactiva (Textual TUI - Predeterminada):**
   ```bash
   uv run python main.py
   # o explícitamente:
   uv run networking-agent --tui
   ```
   - **60 FPS & Multihilo:** Las conexiones SSH de Netmiko y las llamadas a la IA corren en hilos de trabajo independientes (`@work(thread=True)`), manteniendo la interfaz 100% fluida.
   - **Atajos de teclado:**
     - `q`: Salir del asistente.
     - `d`: Registrar nuevo equipo (abre modal con validación y cifrado).
     - `s`: Configurar proveedor y modelo de IA (Ollama / Gemini).
     - `r`: Recargar lista de equipos y tabla de auditoría.
     - `y` / `n`: Autorizar o Rechazar remediación en la ventana modal HitL.
     - `Tab` / `Shift+Tab`: Mover el foco entre controles.

2. **Asistente Interactivo Clásico de Consola (Rich Wizard):**
   ```bash
   uv run networking-agent --cli
   # o versión corta:
   uv run python main.py -c
   ```
   Ideal para entornos con terminales mínimos o sin soporte completo de eventos de ratón.

3. **Ejecución Automatizada en Modo Lote (CI/CD / Scripts):**
   ```bash
   uv run networking-agent \
     --provider ollama \
     --model netexpert:latest \
     --device-host 10.10.20.11 \
     --device-type cisco_nxos \
     --mode PROACTIVE \
     --log-message "OSPF MTU mismatch en Ethernet1/1"
   ```

### 3.3. Configuración Dinámica y Bóveda Criptográfica

---

## 4. Gestión de Inventario de Dispositivos

El asistente permite registrar y persistir dispositivos de red de múltiples fabricantes.

### 4.1. Plataformas y Vendors Soportados

| Identificador (`device_type`) | Fabricante y Sistema Operativo | Familia de Equipos Típica |
|---|---|---|
| `cisco_ios` | Cisco IOS / IOS-XE | Catalyst 2960/3850/9300, ISR 4000, ASR 1000 |
| `cisco_nxos` | Cisco NX-OS (Nexus) | Nexus 3000, 7000, 9000 (Data Center) |
| `cisco_xr` | Cisco IOS-XR | ASR 9000, NCS 5500 (Carrier Routing) |
| `juniper_junos` | Juniper Junos OS | Routers MX, Firewalls SRX, Switches EX/QFX |
| `mikrotik_routeros` | MikroTik RouterOS v6 / v7 | Cloud Core Router (CCR), RouterBOARD (RB), hEX |

### 4.2. Registrar un Nuevo Dispositivo

Desde el menú interactivo:
1. Selecciona **`[2] Gestionar Inventario de Dispositivos`**.
2. Selecciona **`[+] Registrar Nuevo Dispositivo`**.
3. Ingresa los datos solicitados:
   - **Nombre Identificador:** Ej. `Core-Mikrotik-Gateway`
   - **Host / IP:** Ej. `192.168.99.1` *(Valida sintaxis y bloquea path traversal)*
   - **Plataforma:** Selecciona de la lista (ej. `mikrotik_routeros`)
   - **Puerto SSH:** `22` (por defecto)
   - **Usuario SSH:** Ej. `admin`
   - **Contraseña:** Se solicita de forma enmascarada y se cifra con Fernet antes de guardarse en SQLite.

---

## 5. Modos de Operación

Al seleccionar **`[1] Iniciar Diagnóstico y Remediación Asistida`**, se despliegan dos modalidades operativas:

### 5.1. Modo Proactivo (Diagnóstico por Síntomas)

En este modo, el operador describe en lenguaje natural lo que experimenta la red o los usuarios finales.

**Ejemplo de síntomas comunes:**
- *"Siento lento el internet y cuesta mucho abrir páginas web."*
- *"El router presenta pérdidas intermitentes del 20% en la red LAN."*
- *"Los usuarios conectados al puerto ether2 se quejan de lentitud extrema."*
- *"Se cayeron las sesiones de BGP con el proveedor secundario."*

#### Flujo Proactivo:
1. El asistente se conecta vía SSH al router objetivo en modo de solo lectura.
2. Descubre dinámicamente qué interfaz sostiene la IP de administración remota y la ruta por defecto (`0.0.0.0/0`) mediante `discover_active_management_interfaces()`.
3. Ejecuta comandos de diagnóstico en vivo (CPU, estado de interfaces, errores de paquetes, estadísticas de ruta, DNS).
4. Ensambla un contexto técnico completo y lo envía al cerebro de IA (`Ollama` o `Gemini`).
5. La IA diagnostica la causa raíz y determina si se requiere un cambio en la configuración.

### 5.2. Modo Reactivo (Ingesta de Telemetría / Syslog)

Orientado a responder a alertas generadas por sistemas de monitorización (Zabbix, PRTG, Grafana, SIEM o Syslog central).

**Ejemplos de eventos de telemetría:**
- **Cisco Duplex Mismatch:**  
  `%CDP-4-DUPLEX_MISMATCH: Full/half duplex mismatch detected on GigabitEthernet1/0/2`
- **Cisco Err-Disabled:**  
  `%PM-4-ERR_DISABLE: link-flap error detected on Gi1/0/5, putting Gi1/0/5 in err-disable state`
- **Junos Interface Down:**  
  `SNMP_TRAP_LINK_DOWN: ifIndex 508, ifAdminStatus up(1), ifOperStatus down(2), ifName ge-0/0/1`
- **MikroTik BGP Drop:**  
  `bgp,connection,error Remote closed connection (peer: 10.255.0.1)`

---

## 6. Flujo Interactivo Human-in-the-Loop (HitL)

La seguridad operativa es primordial. **Ningún cambio se aplica de forma autónoma sin autorización explícita de un ingeniero.**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Propiedad                ┃ Valor Diagnóstico                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Severidad                │ HIGH                                                │
│ Causa Raíz Diagnosticada │ Pérdida de paquetes en LAN ether2 por dúplex half. │
│ Acción Propuesta         │ set_interface_duplex_full                           │
│ Requiere Cambio          │ True                                                │
│ Interfaz Objetivo        │ ether2                                              │
└━━━━━━━━━━━━━━━━━━━━━━━━━━┴━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘
```

### Puerta de Aprobación Humana:

El operador visualiza:
- Diagnóstico técnico detallado.
- Dispositivo objetivo y usuario.
- **Previsualización exacta de comandos CLI nativos a inyectar.**
- Mecanismo de reversión y rollback garantizado.

```text
¿Autoriza la ejecución de estos cambios en el equipo? (s/n) [n]: 
```

> **Sistema de Repregunta Continua:**  
> Si el operador comete un error tipográfico o presiona una tecla accidentalmente, el asistente **no cancela abruptamente ni ejecuta cambios no deseados**. Explica las opciones válidas (`s / si / y` para autorizar, `n / no` para rechazar) y vuelve a consultar educadamente.

---

## 7. Guardarraíles de Seguridad y Blast Radius

### 7.1. Blindaje de la Interfaz WAN y Gestión Remota
El asistente cuenta con una política de seguridad estricta:
- **Interfaces WAN y Enlaces de Acceso:**  
  Si un síntoma reporta "internet lento" o "link flapping histórico", pero la interfaz WAN (`ether1`, `GigabitEthernet0/0/0`, `fxp0`, etc.) está activa con 0 errores actuales de paquetes, el asistente **prohíbe tajantemente proponer `restart_interface` o `disable_interface`**.
- **Razón técnica:** Reiniciar una interfaz WAN o de gestión corta la sesión SSH remota, interrumpe túneles VPN y llamadas VoIP, provocando un apagón crítico que requeriría acceso físico por cable de consola.

### 7.2. Filtro de Inyección de Comandos (`CommandValidator`)
Todo comando generado por los drivers se somete a una inspección estricta antes de enviarse al transporte SSH. Se rechazan:
- Descargas de binarios externos (`tool fetch`, `tftp-server`).
- Creación de usuarios o puertas traseras (`user add`, `login user`, `password`).
- Pruebas de estrés que saturen el enlace (`traffic-generator`).
- Proxies no autorizados (`ip socks`, `ip proxy`).
- Scripts y schedulers persistentes (`system script`, `system scheduler`).
- Encadenamiento shell (`&&`, `|`, `;`, `\`, backticks).

---

## 8. Verificación Post-Cambio y Rollback Autónomo

Una vez autorizada la operación por el ingeniero humano:

1. **Snapshot Pre-Cambio:**  
   Se descarga una copia íntegra de la configuración activa a la carpeta `backups/<host>_<timestamp>.cfg`. En plataformas compatibles (NX-OS y MikroTik), se crea adicionalmente un punto de restauración hardware nativo.
2. **Inyección Transaccional:**  
   Se envían los comandos validados utilizando la sesión SSH activa reutilizada (sin reconexiones lentas). En Junos e IOS-XR se aplican con temporizador de confirmación (`commit confirmed 3`).
3. **Verificación Post-Cambio:**  
   El motor [`VerificationEngine`](../src/networking_agent/engine/verification.py) realiza una segunda interrogación de telemetría y compara el estado contra el snapshot inicial.
4. **Rollback de Emergencia:**  
   Si el problema persiste, la interfaz sigue caída o se detectan errores adicionales, el agente dispara el rollback de inmediato restaurando el snapshot previo y alertando al operador.

---

## 9. Auditoría y Trazabilidad

Cada acción, diagnóstico, intento de inyección bloqueado, autorización u orden de rollback se registra en formato **JSONL inmutable**:

- **Ruta de auditoría:** [`logs/audit.jsonl`](../logs/audit.jsonl)
- **Campos registrados:**
  - `timestamp`: Fecha y hora UTC precisa en estándar ISO 8601.
  - `event_type`: Tipo de evento (`NO_OP`, `OPERATOR_REJECTED`, `SECURITY_REJECTED`, `INJECTION_REJECTED`, `REMEDIATION_SUCCESS`, `REMEDIATION_ROLLBACK`).
  - `device_host`: Host del equipo afectado.
  - `action`: Acción solicitada.
  - `commands`: Lista exacta de comandos CLI ejecutados.
  - `approved`: Si contó con autorización humana.
  - `verification_status`: `PASSED` o `FAILED`.

---

## 10. Solución de Problemas Frecuentes (FAQ)

### P: ¿Por qué el modelo dice que no se requieren cambios si reporté que el internet está lento?
**R:** Si las estadísticas de tu router muestran bajo uso de CPU, 0 paquetes descartados (`drop`) y 0 errores físicos (`rx/tx error`), reiniciar la interfaz WAN no solucionará el problema y causará desconexión. El asistente identifica que la lentitud probablemente proviene de congestión local por descargas de otros usuarios, interferencia Wi-Fi o límites de ancho de banda del proveedor ISP.

### P: ¿Cómo puedo cambiar entre Ollama y Gemini rápidamente?
**R:** En el menú principal selecciona la opción `[3] Configuración y Claves de API` o establece la variable `AI_PROVIDER=gemini` en tu archivo `.env`.

### P: ¿Dónde se guardan las contraseñas de los routers?
**R:** Se guardan en la base de datos local `data/networking_agent.db`. Las contraseñas se almacenan cifradas mediante el algoritmo simétrico Fernet (AES-128-CBC con HMAC). La clave maestra en `data/.vault.key` está blindada con permisos `0600` de modo que solo tu usuario del sistema operativo tiene acceso a ella.
