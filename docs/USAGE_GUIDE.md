# 📖 Guía Completa de Uso y Operación: NetworkingAgent Enterprise v2.0

Bienvenido a la guía oficial de usuario y operaciones para **NetworkingAgent Enterprise v2.0**, la plataforma autónoma de ingeniería de redes con automatización en bucle cerrado (*Closed-Loop Automation*), inferencia de inteligencia artificial multi-cerebro y terminal reactiva de alto rendimiento.

---

## 📑 Tabla de Contenidos

1. [Visión General de la Versión 2.0](#1-visión-general-de-la-versión-20)
2. [Requisitos Previos y Entorno](#2-requisitos-previos-y-entorno)
3. [Instalación Rápida con uv](#3-instalación-rápida-con-uv)
4. [Configuración Inicial y Bóveda Criptográfica](#4-configuración-inicial-y-bóveda-criptográfica)
5. [Navegación en la Terminal Reactiva (Textual TUI)](#5-navegación-en-la-terminal-reactiva-textual-tui)
6. [Pilar 1: Modo Troubleshooting Autónomo](#6-pilar-1-modo-troubleshooting-autónomo)
7. [Pilar 2: Modo Configuración Declarativa](#7-pilar-2-modo-configuración-declarativa)
8. [Pilar 3: Modo Automatización y Despliegue en Lote (Jinja2 & Dry-Run)](#8-pilar-3-modo-automatización-y-despliegue-en-lote-jinja2--dry-run)
9. [Pilar 4: Inventario de Dispositivos y Verificación de Conectividad](#9-pilar-4-inventario-de-dispositivos-y-verificación-de-conectividad)
10. [Pilar 5: Registro de Auditoría y Trazabilidad Inmutable](#10-pilar-5-registro-de-auditoría-y-trazabilidad-inmutable)
11. [Guardarraíles de Seguridad y Blast Radius](#11-guardarraíles-de-seguridad-y-blast-radius)
12. [Preguntas Frecuentes (FAQ)](#12-preguntas-frecuentes-faq)

---

## 1. Visión General de la Versión 2.0

La versión 2.0 de **NetworkingAgent** transforma el asistente de diagnóstico reactivo en una plataforma integral de ingeniería de redes autónoma estructurada en **tres pilares operacionales clave** accesibles desde una interfaz TUI moderna construida sobre [Textual](https://textual.textualize.io/):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        NETWORKINGAGENT ENTERPRISE v2.0                                 │
│                                                                                        │
│   [1. TROUBLESHOOTING]          [2. CONFIGURACIÓN]          [3. AUTOMATIZACIÓN]       │
│   Diagnóstico autónomo y       Aprovisionamiento multi-     Editor de plantillas,      │
│   análisis de causa raíz en    protocolo en lenguaje        validación dry-run y       │
│   lenguaje natural (L1-L7).    natural con diff y rollback. despliegue en lote.        │
│                                                                                        │
│                [4. INVENTARIO]                 [5. AUDITORÍA]                          │
│                Gestión de routers/switches     Bitácora JSONL inmutable de             │
│                y prueba de conectividad SSH.   eventos, cambios y rollbacks.           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Requisitos Previos y Entorno

- **Sistema Operativo:** Linux (Ubuntu, Debian, RHEL, Arch), macOS o Windows (PowerShell nativo o WSL2).
- **Python:** Versión `>= 3.12` (Recomendado: Python `3.14`).
- **Gestor de Paquetes:** [`uv`](https://github.com/astral-sh/uv) (Recomendado para resolución determinista e instantánea).
- **Conectividad de Red:** Acceso TCP puerto 22 (SSH) hacia los routers, switches o firewalls gestionados.
- **Cerebro de IA:**
  - **Opción Soberana / Local (Privacidad 100% On-Premise):** [Ollama](https://ollama.com/) ejecutando modelos locales como `qwen2.5-coder:14b`, `netexpert:latest` o `llama3.1`.
  - **Opción Cloud Enterprise:** Llaves de API para **Google Gemini** (`gemini-2.5-pro`, `gemini-2.5-flash`), **OpenAI** (`gpt-4o`) o **Anthropic Claude** (`claude-3-5-sonnet`).

---

## 3. Instalación Rápida con uv

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd networkingAgent

# 2. Sincronizar el entorno virtual y dependencias con uv
uv sync --extra dev

# 3. Validar la integridad de la suite de pruebas (125/125 pruebas passing)
uv run --no-sync pytest

# 4. Verificar conformidad del linter
uv run --no-sync ruff check .
```

---

## 4. Configuración Inicial y Bóveda Criptográfica

NetworkingAgent almacena credenciales y configuraciones en una base de datos local SQLite (`data/networking_agent.db`) protegida con modo WAL (*Write-Ahead Logging*) y cifrado simétrico Fernet (AES-128-CBC con autenticación HMAC-SHA256).

### 4.1. Archivo de Entorno (`.env`)

Copia la plantilla `.env.example`:

```bash
cp .env.example .env
```

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `AI_PROVIDER` | Proveedor cerebral activo (`ollama`, `gemini`, `openai`, `anthropic`) | `ollama` |
| `AI_MODEL` | Modelo de lenguaje específico a invocar | `qwen2.5-coder:14b` |
| `OLLAMA_HOST` | URL base de la API de Ollama | `http://localhost:11434` |
| `GEMINI_API_KEY` | Llave de API para Google Gemini | `None` |
| `OPENAI_API_KEY` | Llave de API para OpenAI | `None` |
| `ANTHROPIC_API_KEY` | Llave de API para Anthropic Claude | `None` |
| `ENFORCE_GUARDRAILS` | Bloqueo activo de blast radius y comandos shell | `true` |
| `AUTO_ROLLBACK_ON_FAILURE` | Reversión automática si falla la post-verificación | `true` |
| `SSH_TIMEOUT` | Timeout en segundos para comandos Netmiko | `30` |

### 4.2. Modal Dinámico de Ajustes de IA (`s` o botón `Ajustes IA`)

La aplicación incluye una ventana modal adaptativa que reconfigura dinámicamente sus campos y niveles de enmascaramiento según el proveedor seleccionado:

- Al elegir **Ollama**, el campo de llave de API se oculta automáticamente y se ofrece el endpoint local `http://localhost:11434`.
- Al elegir **Google Gemini**, **OpenAI** o **Anthropic Claude**, se solicita la llave correspondiente con enmascaramiento por contraseña y cifrado inmediato antes de persistir en SQLite.
- Permite conmutar la bandera `Modo Auto-Approve` para entornos de pruebas automatizadas o mantener el control humano obligatorio (*Human-in-the-Loop*).

---

## 5. Navegación en la Terminal Reactiva (Textual TUI)

Inicia el agente con el comando principal:

```bash
uv run python main.py
# O alternativamente:
uv run networking-agent --tui
```

### 5.1. Atajos de Teclado Globales

| Atajo | Función |
|:---:|---|
| `1` | Acceso directo a **Troubleshooting Autónomo** |
| `2` | Acceso directo a **Configuración Declarativa** |
| `3` | Acceso directo a **Automatización y Plantillas Jinja2** |
| `4` | Acceso directo a **Inventario de Dispositivos** |
| `5` | Acceso directo a **Registro de Auditoría** |
| `h` | **Volver al Dashboard de Inicio** desde cualquier vista |
| `s` | Abrir la **Bóveda de Configuración de IA** |
| `d` | Abrir el modal de **Registro de Nuevo Dispositivo** |
| `r` | **Recargar datos** (inventario y bitácora de auditoría) |
| `q` | **Salir** de la aplicación |
| `Tab` / `Shift+Tab` | Mover el foco entre campos, botones y paneles |

### 5.2. Modo Consola Clásico (Rich Wizard)

Para sesiones remotas vía terminales seriales o sin soporte de eventos de ratón:

```bash
uv run networking-agent --cli
```

---

## 6. Pilar 1: Modo Troubleshooting Autónomo

Diseñado para resolver incidencias complejas en tiempo real a partir de síntomas descritos en **lenguaje natural**.

```
[Operador describe síntoma] 
         │
         ▼
[Interrogación en Vivo SSH] ──► Ejecuta show commands dinámicos (BGP, OSPF, interfaces, errores)
         │
         ▼
[Inferencia del Cerebro IA] ──► Identifica causa raíz en L1-L7 y emite NetworkIntent neutral
         │
         ▼
[Blast Radius Guard]       ──► Verifica que NO afecte interfaces WAN o IP de administración
         │
         ▼
[Compuerta HitL]           ──► Operador revisa diagnóstico y autoriza comandos CLI propuestos
         │
         ▼
[Snapshot & Ejecución]     ──► Respaldo atómico + inyección CLI + rollback si falla post-check
```

### 6.1. Flujo de Operación Paso a Paso

1. Desde el Menú Principal, presiona `1` o haz clic en **1. TROUBLESHOOTING**.
2. En la barra lateral izquierda, selecciona el equipo sobre el cual se reporta el incidente (ej. `Edge-Cisco-Router`).
3. En el campo **Descripción del Síntoma Operativo**, redacta lo que ocurre en lenguaje natural:
   - *"Los usuarios en la VLAN 10 reportan lentitud extrema y caída de llamadas VoIP hacia el conmutador central."*
   - *"El vecino BGP con el proveedor secundario 192.168.50.2 está en estado Idle o Active."*
   - *"Se detectan errores de CRC y paquetes descartados en la interfaz de enlace LAN ether2."*
4. Haz clic en **Diagnosticar Síntoma (IA)**.
5. El agente ejecuta comandos de diagnóstico en caliente (`get_troubleshooting_commands`) para recopilar telemetría de interfaces, errores físicos, vecinos OSPF/BGP y utilización de CPU.
6. La IA correlaciona los datos y presenta la causa raíz en una tarjeta diagnóstica con severidad (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
7. Si el problema amerita una remediación técnica, se presenta la compuerta **Human-in-the-Loop** mostrando el *diff* de comandos exactos.
8. Al autorizar (`s`), el agente toma un snapshot de respaldo del equipo, aplica el cambio y re-interroga el estado para certificar la resolución.

---

## 7. Pilar 2: Modo Configuración Declarativa

Permite solicitar modificaciones y aprovisionamiento de red en **lenguaje natural**, traduciendo la intención en comandos nativos multi-fabricante con estricta validación sintáctica y mecanismo de reversión.

### 7.1. Protocolos Soportados

| Protocolo / Categoría | Ejemplos de Solicitud en Lenguaje Natural | Fabricantes Compatibles |
|---|---|---|
| **BGP** | *"Levanta una sesión eBGP con el peer 192.168.10.2 en AS 65100 con soft-reconfiguration inbound."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **OSPF** | *"Configura OSPF proceso 1 área 0 en GigabitEthernet0/1 con Router-ID 1.1.1.1 y red 10.0.0.0/24."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **EIGRP** | *"Habilita EIGRP AS 100 para la subred 172.16.0.0/16 con interfaz pasiva por defecto."* | Cisco IOS, Cisco NX-OS |
| **VLAN & SVI** | *"Crea la VLAN 100 llamada VENTAS con la IP 192.168.100.1/24 y descríbela."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **STP** | *"Habilita Rapid Spanning-Tree con prioridad de puente 4096 y activa BPDU Guard en puertos de acceso."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **Port-Channel** | *"Crea el Port-Channel 5 en modo activo LACP agrupando GigabitEthernet0/1 y GigabitEthernet0/2."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **ACLs** | *"Crea una lista de acceso extendida que bloquee tráfico Telnet pero permita SSH y tráfico web hacia la DMZ."* | Cisco IOS, NX-OS, Junos, RouterOS |
| **Servicios** | *"Configura NTP al servidor 10.10.10.123 y envía logs de syslog a 10.10.10.514 con nivel warnings."* | Cisco IOS, NX-OS, Junos, RouterOS |

### 7.2. Flujo de Configuración

1. Presiona `2` o selecciona **2. CONFIGURACION**.
2. Selecciona el dispositivo objetivo en la barra lateral.
3. Elige la categoría de protocolo (o déjalo en detección automática).
4. Describe la intención en lenguaje natural:
   ```text
   Configura una sesión BGP vecina con el router 10.255.0.2 bajo el sistema autónomo 64512.
   Agrega descripción 'Enlace Primario Datacenter' y anuncia la red 192.168.50.0/24.
   ```
5. Presiona **Sintetizar y Aplicar Configuración**.
6. El motor genera una instancia de [`ConfigurationIntent`](../src/networking_agent/models/config_intent.py) con tres bloques de comandos:
   - **Comandos Candidatos:** Sintaxis CLI nativa generada para el sistema operativo destino.
   - **Comandos de Verificación:** Comandos de solo lectura para auditar el estado posterior (ej. `show ip bgp summary`).
   - **Comandos de Rollback:** Sentencias de negación para revertir el cambio atómicamente si el operador lo decide.
7. Al confirmar en la compuerta HitL, se ejecuta el snapshot, se inyectan los comandos y se ejecutan las verificaciones post-despliegue.

---

## 8. Pilar 3: Modo Automatización y Despliegue en Lote (Jinja2 & Dry-Run)

El motor de automatización está diseñado para el despliegue masivo y repetible de configuraciones sobre flotas de dispositivos heterogéneos.

### 8.1. Editor de Texto Integrado (`TextArea`)

La vista de Automatización dispone de un editor de texto interactivo con:
- Numeración de líneas.
- Capacidad para escribir, pegar o modificar scripts CLI o plantillas Jinja2 en tiempo real.
- Selector de plantillas pre-cargadas que autocompleta el área de trabajo.

### 8.2. Catálogo de Plantillas Jinja2 Pre-Cargadas

1. **Hardening Base y Seguridad (Cisco IOS/XE):** Cifrado de contraseñas locales (`service password-encryption`), deshabilitación de servidores HTTP inseguros, bloqueo de source routing y restricción de líneas VTY a transporte exclusivo por SSH con timeout de 10 minutos.
2. **Aprovisionamiento de VLAN y SVI (Cisco IOS/XE):** Creación parametrizada de VLAN con identificador, nombre, interfaz SVI con IP/máscara y comando `no shutdown`.
3. **Enrutamiento OSPF Área 0 (Cisco IOS/XE):** Inicialización de proceso OSPF monorárea con Router-ID, declaración de red y definición de interfaces pasivas por seguridad.
4. **Servicios NTP y Syslog Corporativo (Cisco IOS/XE):** Configuración de servidores de tiempo de red y reenvío de trampas de log hacia SIEM con marcas de tiempo en milisegundos.
5. **Junos: Creación de VLAN e Interfaz IRB (Juniper Junos):** Sintaxis jerárquica Junos para creación de VLANs 802.1Q con subinterfaz de enrutamiento integrado IRB.

### 8.3. Validador de Sintaxis en Seco (*Dry-Run* Pre-Flight)

Antes de conectar a cualquier equipo, presiona **Validar Sintaxis (Dry-Run)**. El analizador estático [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py) ejecuta inspecciones exhaustivas:

- **Detección de Comandos Destructivos:** Bloquea tajantemente comandos de reinicio (`reload`, `reboot`), borrado de configuraciones (`erase startup-config`, `write erase`, `zeroize`) o reset de fábrica (`/system reset-configuration`).
- **Variables Jinja2 sin Renderizar:** Alerta si existen etiquetas huérfanas `{{ variable }}` o `{% for ... %}` que provocarían fallos sintácticos en el switch.
- **Balance de Bloques Jerárquicos en Junos:** Cuenta y verifica la paridad exacta entre llaves de apertura `{` y cierre `}`.
- **Prefijos Obligatorios en RouterOS:** Verifica que los comandos para MikroTik comiencen correctamente con `/` o `:`.
- **Comillas Desbalanceadas:** Detecta comillas dobles o simples impares.

### 8.4. Despliegue en Lote con `BatchDeployer`

1. En la lista de selección múltiple (**Equipos Objetivo del Despliegue**), marca las casillas de los routers o switches a aprovisionar.
2. Haz clic en **Desplegar en Equipos**.
3. El orquestador [`BatchDeployer`](../src/networking_agent/engine/automation.py):
   - Asigna un identificador único de lote (`job_id`).
   - Para cada equipo objetivo:
     1. Establece sesión SSH mediante el pool de conexiones.
     2. Genera un snapshot íntegro de la configuración activa (`backups/<host>_<timestamp>.cfg`).
     3. Inyecta los comandos validados.
     4. Si ocurre un fallo en un equipo en particular, ejecuta automáticamente el rollback sobre ese dispositivo específico restaurando su snapshot sin comprometer a los equipos que concluyeron exitosamente.
     5. Registra el evento en la bitácora de auditoría inmutable.

---

## 9. Pilar 4: Inventario de Dispositivos y Verificación de Conectividad

Permite la administración centralizada del catálogo de infraestructura:

- **Alta de Dispositivos (`d`):** Modal con validación de IP/Host (prevención de *path traversal*), selección de fabricante (`cisco_ios`, `cisco_nxos`, `cisco_xr`, `juniper_junos`, `mikrotik_routeros`), puerto SSH, usuario y contraseña.
- **Cifrado en Reposo:** Las credenciales nunca se almacenan en texto plano; se cifran con Fernet antes de guardarse en SQLite.
- **Prueba de Conectividad en Vivo:** Al seleccionar un equipo en la tabla, el botón **Probar Conectividad SSH** abre un socket contra el router, verifica autenticación y mide la latencia de respuesta en milisegundos.

---

## 10. Pilar 5: Registro de Auditoría y Trazabilidad Inmutable

Cumple con estándares corporativos de cumplimiento y seguridad (SOC2, ISO 27001):

- **Bitácora JSONL:** Cada acción se registra inmediatamente en [`logs/audit.jsonl`](../logs/audit.jsonl).
- **Visor en Tiempo Real:** La vista 5 de la TUI muestra los últimos eventos ordenados cronológicamente:
  - `TROUBLESHOOTING_RESOLVED`: Diagnóstico completado sin necesidad de cambio.
  - `TROUBLESHOOTING_REMEDIATED`: Remediación aplicada y verificada con éxito.
  - `CONFIGURATION_APPLIED`: Despliegue de configuración declarativa completado.
  - `BATCH_DEPLOYMENT_SUCCESS`: Lote de automatización aplicado exitosamente.
  - `SECURITY_REJECTED`: Intento de inyección de comandos o violación de blast radius bloqueado.
  - `OPERATOR_REJECTED`: Propuesta de cambio declinada por el ingeniero humano.

---

## 11. Guardarraíles de Seguridad y Blast Radius

### 11.1. Protección Activa de Interfaces de Gestión y WAN
[`BlastRadiusGuard`](../src/networking_agent/guardrails/blast_radius.py) descubre dinámicamente qué interfaz sostiene la IP de administración SSH del router mediante `discover_active_management_interfaces()`. Queda prohibido incondicionalmente ejecutar `shutdown` o reinicios sobre dichas interfaces, previniendo aislamiento accidental.

### 11.2. Validador de Inyección de Comandos (`CommandValidator`)
Rechaza cualquier comando que intente:
- Encadenar sentencias shell mediante metacaracteres (`&&`, `|`, `;`, `` ` ``, `$`).
- Crear cuentas de usuario privilegiadas o alterar contraseñas administrativas.
- Instalar túneles o proxies no autorizados (`tool fetch`, `ip socks`, `ip proxy`).

---

## 12. Preguntas Frecuentes (FAQ)

### P: ¿Qué ocurre si un despliegue en lote falla en uno de diez switches?
**R:** `BatchDeployer` opera con aislamiento por dispositivo. Si el switch #4 experimenta un error de sintaxis o desconexión, el agente ejecuta el rollback exclusivo sobre el switch #4 restaurando su snapshot previo, mientras que los switches restantes mantienen su configuración aplicada exitosamente.

### P: ¿Puedo usar el agente sin conexión a Internet?
**R:** Sí. Configura `AI_PROVIDER=ollama` con un modelo local (`qwen2.5-coder:14b` o `netexpert:latest`). Todo el procesamiento de lenguaje natural, telemetría y diagnósticos se ejecutará 100% de manera soberana en tu propia máquina o servidor sin enviar un solo byte a la nube.

### P: ¿Cómo restauro manualmente un snapshot de respaldo si es necesario?
**R:** Los snapshots se guardan en texto plano en la carpeta `backups/<host>_<timestamp>.cfg`. Puedes copiar el contenido directamente a la terminal del equipo o utilizar las funciones nativas de rollback (`configure replace flash:<archivo>` en Cisco o `rollback 1` en Junos).
