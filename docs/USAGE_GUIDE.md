# 📖 Guía Completa de Uso y Operación: NetworkingAgent Enterprise v2.1

Bienvenido a la guía oficial de usuario y operaciones para **NetworkingAgent Enterprise v2.1**, la plataforma autónoma de ingeniería de redes con automatización en bucle cerrado (*Closed-Loop Automation*), inferencia de inteligencia artificial multi-cerebro y terminal reactiva de alto rendimiento.

---

## 📑 Tabla de Contenidos

1. [Visión General de la Versión 2.1](#1-visión-general-de-la-versión-21)
2. [Requisitos Previos y Entorno](#2-requisitos-previos-y-entorno)
3. [Instalación Rápida con uv](#3-instalación-rápida-con-uv)
4. [Configuración Inicial y Bóveda Criptográfica](#4-configuración-inicial-y-bóveda-criptográfica)
5. [Navegación en la Terminal Reactiva y Atajos Ergonómicos](#5-navegación-en-la-terminal-reactiva-y-atajos-ergonómicos)
6. [Paleta de Comandos Profesional (Ctrl+P)](#6-paleta-de-comandos-profesional-ctrlp)
7. [Pilar 1: Modo Troubleshooting Autónomo](#7-pilar-1-modo-troubleshooting-autónomo)
8. [Pilar 2: Modo Configuración Declarativa](#8-pilar-2-modo-configuración-declarativa)
9. [Pilar 3: Modo Automatización, Guía de Variables Jinja2 y Despliegue en Lote](#9-pilar-3-modo-automatización-guía-de-variables-jinja2-y-despliegue-en-lote)
10. [Pilar 4: Inventario de Dispositivos y Diagnóstico de Conectividad en Tiempo Real](#10-pilar-4-inventario-de-dispositivos-y-diagnóstico-de-conectividad-en-tiempo-real)
11. [Pilar 5: Registro de Auditoría, Trazabilidad Forense y Exportación](#11-pilar-5-registro-de-auditoría-trazabilidad-forense-y-exportación)
12. [Guardarraíles de Seguridad y Blast Radius](#12-guardarraíles-de-seguridad-y-blast-radius)
13. [Preguntas Frecuentes (FAQ)](#13-preguntas-frecuentes-faq)

---

## 1. Visión General de la Versión 2.1

**NetworkingAgent Enterprise v2.1** estructura las operaciones de ingeniería de redes en **cinco módulos especializados**, coordinados desde una consola de terminal reactiva (`Textual TUI`) con estética *Cyberpunk NOC Mission Control*:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        NETWORKINGAGENT ENTERPRISE v2.1                                 │
│                                                                                        │
│   [1. TROUBLESHOOTING]          [2. CONFIGURACIÓN]          [3. AUTOMATIZACIÓN]       │
│   Diagnóstico autónomo y       Aprovisionamiento multi-     Editor de plantillas,      │
│   análisis de causa raíz en    protocolo en lenguaje        guía interactiva Jinja2 y  │
│   lenguaje natural (L1-L7).    natural con diff y rollback. despliegue masivo en lote. │
│                                                                                        │
│                [4. INVENTARIO]                 [5. AUDITORÍA]                          │
│                Catálogo cifrado y prueba de    Bitácora inmutable SHA-256,             │
│                conectividad en vivo (Ping/SSH).exportación JSON y purga de tests.      │
│                                                                                        │
│   [Paleta de Comandos Global: Ctrl+P] ──► +15 operaciones técnicas y atajos directos   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Requisitos Previos y Entorno

- **Sistema Operativo:** Linux (Ubuntu, Debian, RHEL, Arch), macOS o Windows (PowerShell nativo o WSL2).
- **Python:** Versión `>= 3.12` (Certificado y probado en Python `3.14`).
- **Gestor de Paquetes:** [`uv`](https://github.com/astral-sh/uv) (Recomendado para resolución determinista e instantánea).
- **Conectividad de Red:** Acceso TCP puerto 22 (SSH) hacia los routers, switches o firewalls gestionados.
- **Cerebro de IA:**
  - **Opción Soberana / Local (Privacidad 100% On-Premise):** [Ollama](https://ollama.com/) ejecutando modelos locales como `qwen2.5-coder:14b`, `netexpert:latest` o `llama3.1`.
  - **Opción Cloud Enterprise:** Llaves de API para **Google Gemini** (`gemini-2.5-pro`, `gemini-2.5-flash`), **OpenAI** (`gpt-4o`) o **Anthropic Claude** (`claude-3-5-sonnet`).

---

## 3. Instalación Rápida con uv

```bash
# 1. Clonar el repositorio
git clone https://github.com/GuifMur98/networkingAgent.git
cd networkingAgent

# 2. Sincronizar el entorno virtual y dependencias con uv
uv sync --extra dev

# 3. Validar la integridad de la suite de pruebas (172/172 pruebas passing)
uv run --no-sync pytest

# 4. Verificar conformidad del linter estático (0 advertencias)
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

- Al elegir **Ollama**, se ofrece el botón **Escanear** para detectar modelos instalados localmente en caliente y seleccionar el deseado sin escribir a mano.
- Al elegir **Google Gemini**, **OpenAI** o **Anthropic Claude**, se solicita la llave correspondiente con enmascaramiento por contraseña y cifrado inmediato antes de persistir en SQLite.
- Permite conmutar la bandera `Modo Auto-Approve` para entornos de pruebas automatizadas o mantener el control humano obligatorio (*Human-in-the-Loop*).

---

## 5. Navegación en la Terminal Reactiva y Atajos Ergonómicos

Inicia el agente con el comando principal:

```bash
uv run python main.py
```

### 5.1. Reglas de Filtrado Contextual en el Pie de Página
Para mantener un entorno de trabajo limpio y libre de distracciones operativas:
- **En el Dashboard de Inicio (`pane-home`):** Se muestran todos los atajos generales a la izquierda (`h Inicio`, `q Salir`, `d Nuevo Equipo`, `s Ajustes IA`, `r Recargar`) y el acceso a la Paleta de Comandos a la derecha (`^p Paleta`).
- **En los 5 Módulos Operacionales:** El **único atajo visible en el pie de página es `h Inicio`**. Esto previene pulsaciones accidentales de salida o creación de equipos mientras el operador se encuentra concentrado en un análisis o configuración.
- **Indicadores en Botones:** Todos los botones interactivos que tienen un atajo asignado incluyen su letra entre paréntesis, facilitando el aprendizaje visual:
  - `Volver al Inicio (h)`
  - `+ Registrar Equipo (d)`
  - `Recargar (r)`
  - `Cancelar (Esc)` / `Cerrar (Esc)`
  - `Autorizar y Aplicar (Y)` / `Rechazar y Abortar (N)`

### 5.2. Mapa Completo de Atajos

| Atajo | Contexto | Acción / Destino |
|:---:|:---:|---|
| `1` | Inicio | Abrir Módulo 1: **Troubleshooting** |
| `2` | Inicio | Abrir Módulo 2: **Configuración** |
| `3` | Inicio | Abrir Módulo 3: **Automatización** |
| `4` | Inicio | Abrir Módulo 4: **Inventario de Equipos** |
| `5` | Inicio | Abrir Módulo 5: **Registro de Auditoría** |
| `h` | **Global** | **Volver al Inicio** desde cualquier vista |
| `Ctrl+P` | **Global** | Abrir **Paleta de Comandos** |
| `s` | Inicio | Abrir modal de **Ajustes de IA y Bóveda** |
| `d` | Inicio / Inventario | Abrir modal de **Registrar Nuevo Equipo** |
| `r` | Inicio / Tablas | **Recargar** inventario y bitácora de auditoría |
| `Esc` | Modales | Cancelar formulario o cerrar modal activo |
| `y` / `n` | Modal HitL | **Autorizar (Y)** o **Rechazar (N)** cambios de red |
| `q` | Inicio | **Salir** de la aplicación |

---

## 6. Paleta de Comandos Profesional (`Ctrl+P`)

La **Paleta de Comandos** proporciona acceso centralizado e instantáneo a todas las funciones críticas de la plataforma mediante búsqueda difusa (*fuzzy search*):

```
┌────────────────────────────────────────────────────────────────────────┐
│  > buscar comando...                                                  │
├────────────────────────────────────────────────────────────────────────┤
│  Navegar: Inicio (Dashboard Principal)                                │
│  Navegar: Modulo 1 - Diagnostico y Troubleshooting                    │
│  Navegar: Modulo 2 - Configuracion de Red                             │
│  Navegar: Modulo 3 - Automatizacion y Plantillas                      │
│  Navegar: Modulo 4 - Inventario de Equipos                            │
│  Navegar: Modulo 5 - Auditoria y Bitacora                             │
│  Equipos: Registrar Nuevo Dispositivo en Catalogo                     │
│  Equipos: Diagnostico Completo de Conectividad (Ping + SSH)           │
│  Equipos: Probar Ping ICMP a Dispositivo                              │
│  Equipos: Comprobar Puerto 22 TCP (SSH)                               │
│  Equipos: Sincronizar Catalogo y Recargar Estado                      │
│  Automatizacion: Crear Nueva Plantilla de Configuracion               │
│  Seguridad: Alternar Modo Human-in-the-Loop (Auto-Approve / Manual)   │
│  Diagnostico: Cargar Sintoma Predefinido BGP Caido / Idle             │
│  Diagnostico: Cargar Sintoma Predefinido Duplex Mismatch              │
│  Diagnostico: Cargar Sintoma Predefinido Perdida de Paquetes / CRC   │
│  Auditoria: Exportar Bitacora Forense a Archivo JSON                  │
│  Auditoria: Purgar Registros de Prueba (Limpieza de Auditoria)        │
└────────────────────────────────────────────────────────────────────────┘
```

### Operaciones Disponibles:
1. **Navegación:** Cambia al instante a cualquier módulo sin tocar el ratón.
2. **Equipos y Red:** Ejecuta ping, valida puertos SSH o abre el formulario de alta.
3. **Guardarraíles:** Alterna entre modo manual y auto-aprobación en caliente.
4. **Presets de Síntomas:** Carga rápidamente problemas de red típicos en el área de diagnóstico.
5. **Auditoría:** Descarga o depura eventos de auditoría con un solo comando.

---

## 7. Pilar 1: Modo Troubleshooting Autónomo

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

### Flujo de Operación Paso a Paso:
1. Desde el Menú Principal, presiona `1` o haz clic en **1. TROUBLESHOOTING**.
2. En la barra lateral izquierda, selecciona el equipo sobre el cual se reporta el incidente (ej. `Edge-Cisco-Router`).
3. En el campo **Descripción del Síntoma Operativo**, redacta lo que ocurre o usa los chips rápidos (`BGP Down`, `Duplex Mismatch`, `Pérdida de Paquetes`, `OSPF MTU Mismatch`, `VLAN Trunk Bloqueado`, `Lentitud de Red`).
4. Haz clic en **Ejecutar Troubleshooting Autónomo**.
5. El agente ejecuta comandos de diagnóstico en caliente (`get_troubleshooting_commands`) para recopilar telemetría de interfaces, errores físicos, vecinos OSPF/BGP y utilización de CPU.
6. La IA correlaciona los datos y presenta la causa raíz en una tarjeta diagnóstica con severidad (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
7. Si el problema amerita una remediación técnica, se presenta la compuerta **Human-in-the-Loop** mostrando el *diff* de comandos exactos.
8. Al autorizar (`Y`), el agente toma un snapshot de respaldo del equipo, aplica el cambio y re-interroga el estado para certificar la resolución.

---

## 8. Pilar 2: Modo Configuración Declarativa

Permite solicitar modificaciones y aprovisionamiento de red en **lenguaje natural**, traduciendo la intención en comandos nativos multi-fabricante con estricta validación sintáctica y mecanismo de reversión.

### Protocolos y Selectores Rápidos:
- **BGP:** Sesiones de peering eBGP/iBGP, AS-Path, anuncios de red y filtros.
- **OSPF:** Áreas estándar y stub, Router-ID, temporizadores y autenticación.
- **EIGRP:** Autónomos K-values, subredes y summarization.
- **Enrutamiento Dinámico:** Detección automática del protocolo activo en el equipo.
- **VLAN & Trunk:** Creación de VLANs, encapsulación 802.1Q, SVIs y descripciones.
- **Port-Channel / LACP:** Agrupamiento de interfaces físicas y balanceo de carga.
- **Seguridad / ACL:** Listas de acceso estándar y extendidas con filtrado de puertos.
- **Servicios:** Clientes NTP, servidores Syslog y DNS.

### Flujo de Configuración:
1. Presiona `2` o selecciona **2. CONFIGURACION**.
2. Selecciona el dispositivo objetivo en la barra lateral.
3. Elige la categoría de protocolo deseada mediante los chips superiores.
4. Describe la intención en lenguaje natural:
   ```text
   Configura una sesión BGP vecina con el router 10.255.0.2 bajo el sistema autónomo 64512.
   Agrega descripción 'Enlace Primario Datacenter' y anuncia la red 192.168.50.0/24.
   ```
5. Presiona **Sintetizar y Aplicar Configuración**.
6. El motor genera una instancia de [`ConfigurationIntent`](../src/networking_agent/models/config_intent.py) con tres bloques de comandos:
   - **Comandos Candidatos:** Sintaxis CLI nativa generada para el sistema operativo destino.
   - **Comandos de Verificación:** Comandos de solo lectura para auditar el estado posterior.
   - **Comandos de Rollback:** Sentencias de negación para revertir el cambio atómicamente si el operador lo decide.
7. Al confirmar en la compuerta HitL, se ejecuta el snapshot, se inyectan los comandos y se ejecutan las verificaciones post-despliegue.

---

## 9. Pilar 3: Modo Automatización, Guía de Variables Jinja2 y Despliegue en Lote

El motor de automatización está diseñado para el despliegue masivo y repetible de configuraciones sobre flotas de dispositivos heterogéneos.

### 9.1. Asistente de Creación y Edición de Plantillas Jinja2
Al hacer clic en **+ Nueva** o editar una plantilla existente, se abre un modal especializado que incluye:
- **Nombre y Fabricante Objetivo:** Asociación con Cisco IOS, NX-OS, Junos o RouterOS.
- **Guía de Variables Dinámicas Jinja2:** Panel didáctico integrado explicando el uso de doble llave `{{ nombre_variable }}`.
- **Chips de Variables Rápidas:** Haz clic sobre cualquiera de los chips para insertar el parámetro directamente en la posición del cursor:
  - `vlan_id`, `vlan_name`, `ip_address`, `netmask`, `gateway`, `interface`, `description`, `bgp_as`.
- **Botón Detectar Variables:** Analiza el texto en el editor CLI y notifica cuáles variables Jinja2 están presentes en la plantilla.

### 9.2. Validador de Sintaxis en Seco (*Dry-Run* Pre-Flight)
Antes de conectar a cualquier equipo, presiona **Validar Sintaxis (Dry-Run)**. El analizador estático [`ConfigSyntaxValidator`](../src/networking_agent/guardrails/syntax_validator.py) ejecuta inspecciones exhaustivas:
- **Detección de Comandos Destructivos:** Bloquea tajantemente comandos de reinicio (`reload`, `reboot`), borrado de configuraciones (`erase startup-config`, `write erase`, `zeroize`) o reset de fábrica (`/system reset-configuration`).
- **Variables Jinja2 sin Renderizar:** Alerta si existen etiquetas huérfanas `{{ variable }}` o `{% for ... %}` que provocarían fallos sintácticos en el switch.
- **Balance de Bloques Jerárquicos en Junos:** Cuenta y verifica la paridad exacta entre llaves de apertura `{` y cierre `}`.
- **Prefijos Obligatorios en RouterOS:** Verifica que los comandos para MikroTik comiencen correctamente con `/` o `:`.

### 9.3. Despliegue en Lote con `BatchDeployer`
1. En la lista de selección múltiple (**Equipos Objetivo del Despliegue**), marca las casillas de los routers o switches a aprovisionar (o utiliza los botones rápidos **Todos** / **Ninguno**).
2. Haz clic en **Ejecutar Despliegue en Lote**.
3. El orquestador ejecuta el despliegue transaccional con aislamiento individual: si un equipo falla, solo ese equipo ejecuta rollback hacia su snapshot previo sin afectar a los demás.

---

## 10. Pilar 4: Inventario de Dispositivos y Diagnóstico de Conectividad en Tiempo Real

Gestiona el catálogo de infraestructura y verifica la accesibilidad física y lógica de cada router:

### 10.1. Pruebas de Red en Vivo
Desde la barra de herramientas de la tabla de inventario:
- **Hacer Ping (ICMP):** Envía ráfagas de paquetes ICMP Echo Request para calcular latencia en milisegundos y porcentaje de paquetes recibidos.
- **Probar Conexión (SSH):** Abre un socket TCP hacia el puerto 22 configurado para confirmar que el demonio SSH está escuchando antes de lanzar sesiones Netmiko.
- **Test Completo:** Combina ambas comprobaciones y emite un veredicto consolidado de accesibilidad.

### 10.2. Alta y Gestión Cifrada
- Presiona `d` o haz clic en **+ Registrar Equipo (d)** para abrir el formulario modal.
- Todas las contraseñas y secretos Enable se cifran con Fernet (AES-128-CBC) antes de almacenarse en la base de datos SQLite en modo WAL.

---

## 11. Pilar 5: Registro de Auditoría, Trazabilidad Forense y Exportación

Cumple con estándares corporativos de cumplimiento y seguridad (SOC2, ISO 27001):

### 11.1. Trazabilidad Criptográfica SHA-256
Cada operación ejecutada por el agente genera una entrada inmutable con:
- Timestamp UTC de alta precisión.
- Host y fabricante del equipo.
- Resumen de la acción ejecutada (`TROUBLESHOOTING`, `CONFIGURATION`, `BATCH_DEPLOYMENT`).
- Hash SHA-256 de integridad para garantizar que el registro no ha sido alterado.

### 11.2. Herramientas de Gestión
- **Filtros Dinámicos:** Selector por dispositivo y por estado (`ALL`, `SUCCESS`, `FAILED`, `ROLLBACK`, `BLOCKED`).
- **Exportar JSON:** Exporta la bitácora filtrada o completa hacia un archivo JSON estructurado para auditorías externas o SIEM.
- **Purgar Tests:** Botón de limpieza segura que remueve registros transitorios o de prueba preservando la bitácora de producción.

---

## 12. Guardarraíles de Seguridad y Blast Radius

### 12.1. Protección Activa de Interfaces de Gestión y WAN
[`BlastRadiusGuard`](../src/networking_agent/guardrails/blast_radius.py) descubre dinámicamente qué interfaz sostiene la IP de administración SSH del router mediante `discover_active_management_interfaces()`. Queda prohibido incondicionalmente ejecutar `shutdown` o reinicios sobre dichas interfaces, previniendo aislamiento accidental.

### 12.2. Validador de Inyección de Comandos (`CommandValidator`)
Rechaza cualquier comando que intente:
- Encadenar sentencias shell mediante metacaracteres (`&&`, `|`, `;`, `` ` ``, `$`).
- Crear cuentas de usuario privilegiadas o alterar contraseñas administrativas.
- Instalar túneles o proxies no autorizados (`tool fetch`, `ip socks`, `ip proxy`).

---

## 13. Preguntas Frecuentes (FAQ)

### P: ¿Qué ocurre si un despliegue en lote falla en uno de diez switches?
**R:** `BatchDeployer` opera con aislamiento por dispositivo. Si el switch #4 experimenta un error de sintaxis o desconexión, el agente ejecuta el rollback exclusivo sobre el switch #4 restaurando su snapshot previo, mientras que los switches restantes mantienen su configuración aplicada exitosamente.

### P: ¿Puedo usar el agente sin conexión a Internet?
**R:** Sí. Configura `AI_PROVIDER=ollama` con un modelo local (`qwen2.5-coder:14b` o `netexpert:latest`). Todo el procesamiento de lenguaje natural, telemetría y diagnósticos se ejecutará 100% de manera soberana en tu propia máquina o servidor sin enviar un solo byte a la nube.

### P: ¿Cómo abro la Paleta de Comandos rápidamente?
**R:** Presiona `Ctrl+P` desde cualquier pantalla o haz clic en el botón `^p Paleta` anclado en la esquina inferior derecha del Dashboard de Inicio.
