# 🏛️ Arquitectura del Sistema: NetworkingAgent Enterprise v2.1

> **Diseño Arquitectónico Hexagonal, Patrones de Ingeniería Closed-Loop, Threading Model y Garantías de Confiabilidad**

---

## 1. Visión General del Diseño

**NetworkingAgent Enterprise v2.1** está construido bajo el patrón de **Arquitectura Hexagonal (Puertos y Adaptadores)** combinado con automatización en **bucle cerrado (*Closed-Loop Automation*)**. 

El sistema desacopla de manera rigurosa cuatro responsabilidades fundamentales:
1. **Razonamiento Cognitivo:** Los Modelos de Lenguaje (LLMs) operan exclusivamente como motores de inferencia diagnóstica y síntesis lógica; **nunca** emiten comandos CLI directamente hacia los equipos sin pasar por esquemas tipados estrictos (`NetworkIntent` o `ConfigurationIntent`).
2. **Defensa en Profundidad y Guardarraíles:** Ninguna instrucción generada por un operador o un modelo de IA alcanza el transporte SSH sin atravesar el análisis estático preventivo (`ConfigSyntaxValidator`), la validación de comandos prohibidos (`CommandValidator`) y la protección de interfaces de gestión y WAN (`BlastRadiusGuard`).
3. **Ejecución Transaccional Multi-Fabricante:** Los controladores de red (*drivers*) traducen intenciones lógicas a sintaxis nativa de fabricante, gestionan la reutilización de conexiones SSH (*Connection Pooling*), generan snapshots previos al cambio y garantizan la reversión atómica (*Rollback*) si la verificación operativa posterior detecta anomalías.
4. **Presentación Reactiva de Misión Crítica:** Una interfaz de terminal moderna construida sobre Textual desacopla las operaciones intensivas de I/O de red hacia hilos en segundo plano (`@work(thread=True)`), permitiendo una tasa de actualización constante de 60 FPS sin bloqueos ni parpadeos.

```mermaid
flowchart TD
    subgraph PresentationLayer ["1. Capa de Presentación Reactiva (Textual TUI)"]
        TUI["Terminal UI Textual: 60 FPS Asíncrona"]
        PAL["Paleta de Comandos: NetworkAgentCommandProvider (Ctrl+P)"]
        CLI["Rich Wizard CLI Clásico"]
        TUI --- PAL
        TUI -->|Eventos / Mensajes| AG["NetworkAssistantAgent"]
        CLI -->|Comandos| AG
    end

    subgraph CognitiveLayer ["2. Capa Cognitiva Multi-Cerebro"]
        AG -->|Prompt Saneado| BF["AI Brain Factory"]
        BF --> OLL["Ollama (Local / Privado)"]
        BF --> GEM["Google Gemini 2.5"]
        BF --> OAI["OpenAI GPT-4o"]
        BF --> CLA["Anthropic Claude 3.5"]
        OLL -->|Pydantic Output| NI["NetworkIntent (Troubleshooting)"]
        GEM -->|Pydantic Output| CI["ConfigurationIntent (Configuración)"]
        OAI --> NI
        CLA --> CI
    end

    subgraph AutomationLayer ["3. Capa de Automatización y Diagnóstico"]
        TE["TemplateEngine (Jinja2)"] --> SV["ConfigSyntaxValidator (Dry-Run)"]
        SV --> BD["BatchDeployer (Orquestador Multi-Host)"]
        CON["ConnectivityEngine (Ping ICMP + Socket SSH)"]
        BD --> AG
    end

    subgraph GuardrailLayer ["4. Capa de Seguridad y Guardarraíles"]
        NI --> BG{"BlastRadiusGuard"}
        CI --> SV2{"ConfigSyntaxValidator"}
        BG -->|WAN / Mgmt Protegida| BLK1["BLOQUEO: Blast Radius Violation"]
        SV2 -->|Comandos Destructivos / Error| BLK2["BLOQUEO: Syntax / Safety Violation"]
        BG -->|Seguro| CV{"CommandValidator"}
        SV2 -->|Seguro| CV
        CV -->|Inyección Detectada| BLK3["BLOQUEO: Command Injection"]
        CV -->|Aprobado| HITL["Compuerta Human-in-the-Loop (HitL)"]
    end

    subgraph DriverLayer ["5. Capa de Controladores de Red (SSH Pooling)"]
        HITL -->|Autorización Operador| DRV["NetworkOSDriver Base"]
        DRV --> D_IOS["Cisco IOS / IOS-XE"]
        DRV --> D_NX["Cisco NX-OS (Atomic Sessions)"]
        DRV --> D_XR["Cisco IOS-XR (Commit Confirmed)"]
        DRV --> D_JUN["Juniper Junos (Commit Confirmed)"]
        DRV --> D_TIK["MikroTik RouterOS (System Backup)"]
    end

    subgraph ClosedLoopExecution ["6. Ejecución en Bucle Cerrado y Auditoría"]
        DRV --> SNAP["1. Snapshot Pre-Cambio (.cfg / Checkpoint)"]
        SNAP --> EXEC["2. Inyección Transaccional CLI"]
        EXEC --> POST["3. Verificación Post-Cambio (Health / Diag)"]
        POST -->|Éxito| AUD["Auditoría Inmutable SHA-256: SUCCESS"]
        POST -->|Fallo| RBK["Rollback Inmediato a Snapshot"]
        RBK --> AUD_FAIL["Auditoría Inmutable SHA-256: ROLLBACK"]
    end
```

---

## 2. Capas del Sistema y Componentes

### 2.1. Capa de Presentación Reactiva (`src/networking_agent/tui/`)

La interfaz de usuario principal está construida con el framework reactivo **Textual**:

- **`app.py` (`NetworkingAgentTUIApp`):** Controlador principal de la aplicación.
  - Orquesta el montaje y conmutación entre las 5 vistas de la plataforma sin recargas destructivas de pantalla.
  - Ejecuta operaciones de larga duración (SSH de Netmiko, consultas LLM, validación estática y despliegues en lote) en hilos de trabajo asíncronos en segundo plano utilizando el decorador `@work(thread=True)`, garantizando que la interfaz nunca se congele.
  - Implementa filtrado dinámico de atajos mediante `check_action(action, parameters)`: dentro de los módulos únicamente se visualiza `h Inicio`, mientras que en el dashboard se presentan los atajos generales y la paleta de comandos.
- **`commands.py` (`NetworkAgentCommandProvider`):** Proveedor del catálogo técnico para la Paleta de Comandos (`Ctrl+P`).
  - Provee más de 15 operaciones indexadas para búsqueda difusa (*fuzzy search*).
  - Estilizado estricto sin emojis ni iconos, adaptado al estándar NOC corporativo.
- **Vistas Especializadas (`src/networking_agent/tui/widgets/`):**
  - `TroubleshootingWorkspace`: Diagnóstico por síntomas en lenguaje natural, selección de router, chips de síntomas rápidos y visor del informe de causa raíz.
  - `ConfigurationView`: Formulario declarativo para aprovisionamiento multi-protocolo, selector de categoría por chips y visor de candidate CLI diff.
  - `AutomationView`: Editor de plantillas `TextArea` con números de línea, selector de templates Jinja2, botón de validación dry-run y selector múltiple de equipos (`SelectionList`).
  - `DeviceInventoryView`: Tabla de gestión de routers y switches con ejecución en tiempo real de Ping ICMP, comprobación de socket TCP 22 SSH y diagnóstico combinado.
  - `AuditTableWidget`: Visor forense de eventos estructurados con hashes SHA-256, filtrado en caliente por dispositivo/estado, exportación JSON y purga de pruebas.
  - `HomeDashboard`: Tablero de control principal con 5 tarjetas interactivas de navegación.
- **Ventanas Modales Flotantes (`src/networking_agent/tui/modals/`):**
  - `VaultModal`: Configuración adaptativa de proveedor y modelo LLM con escaneo en vivo de modelos locales de Ollama y enmascaramiento dinámico de llaves.
  - `DeviceModal`: Formulario de alta de dispositivos con validación de IP/Host y cifrado automático de credenciales (Fernet).
  - `TemplateModal`: Asistente de creación y edición de plantillas Jinja2 con Guía Interactiva de Variables Dinámicas y chips de inserción rápida.
  - `HitLModal`: Compuerta interactiva de confirmación humana con previsualización de comandos exactos a inyectar y detalles de rollback.

---

### 2.2. Capa Cognitiva Multi-Cerebro (`src/networking_agent/brains/`)

- **`base.py` (`LLMBrain`):** Interfaz abstracta que define los dos contratos de inferencia:
  1. `analyze_event(telemetry_data: str) -> NetworkIntent`: Diagnóstico de incidentes y selección de acción remediadora.
  2. `synthesize_configuration(device_host, vendor_family, natural_request, protocol_hint) -> ConfigurationIntent`: Síntesis declarativa de configuración multi-protocolo.
  - Protege las entradas no confiables mediante delimitadores XML `<telemetry_event>` y directivas en `HARDENED_SYSTEM_PROMPT` y `HARDENED_CONFIG_SYSTEM_PROMPT`.
- **`discovery.py`:** Módulo para la inspección y pre-calentamiento en caché de modelos locales de Ollama instalados en el sistema host.
- **`ollama.py`:** Conector local y soberano que interactúa con el endpoint HTTP de Ollama utilizando salidas estructuradas en formato JSON (`format="json"`).
- **`gemini.py`:** Conector oficial utilizando el SDK `google-genai` para invocar modelos `gemini-2.5-pro` y `gemini-2.5-flash` con forzado estricto de esquema Pydantic (`response_schema`).
- **`openai.py` / `anthropic.py`:** Adaptadores para OpenAI GPT-4o y Anthropic Claude 3.5 Sonnet.
- **`factory.py`:** Factoría dinámica que resuelve el proveedor configurado en tiempo de ejecución.

---

### 2.3. Capa de Modelos de Datos Tipados (`src/networking_agent/models/`)

- **`intent.py` (`NetworkIntent`):** Esquema Pydantic para el Pilar de Troubleshooting:
  - `diagnosis`: Resumen técnico de la causa raíz.
  - `severity`: Severidad (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `requires_config_change`: Booleano estricto.
  - `action`: Catálogo cerrado de acciones remediadoras.
  - `target_interface`: Validador con expresiones regulares multi-vendor que rechaza caracteres shell y saltos de línea.
- **`config_intent.py` (`ConfigurationIntent`, `AutomationTemplate`, `BatchDeploymentResult`):** Esquema Pydantic para los Pilares de Configuración y Automatización:
  - `protocol_type`: Enumeración (`bgp`, `ospf`, `eigrp`, `stp`, `port_channel`, `vlan`, `acl`, `static_route`, `services`, `custom`).
  - `candidate_commands`: Lista de comandos CLI a inyectar, saneados contra metacaracteres shell (`;`, `&&`, `||`, `` ` ``).
  - `verification_commands`: Comandos de solo lectura para auditar el estado posterior.
  - `rollback_commands`: Comandos de negación atómica para reversión inmediata.

---

### 2.4. Capa de Automatización y Diagnóstico de Red (`src/networking_agent/engine/`)

- **`connectivity.py`:** Motor de verificación de conectividad y alcance:
  - Ejecuta pruebas de **Ping ICMP** utilizando subprocesos asíncronos nativos (`asyncio.create_subprocess_exec`) sin bloquear el hilo principal.
  - Ejecuta comprobaciones no invasivas de disponibilidad del puerto **SSH (TCP 22)** mediante conexiones de socket asíncronas con timeout estricto.
- **`conflict_analyzer.py`:** Motor de análisis de colisiones y solapamiento IP:
  - Analiza tablas de enrutamiento y configuraciones de interfaces activas para advertir al operador si una subred planificada colisiona con una interfaz existente antes de tocar el router.
- **`TemplateEngine`:** Gestiona el catálogo de plantillas pre-cargadas (Hardening, VLAN/SVI, OSPF, NTP/Syslog, Junos IRB) y compila plantillas Jinja2 en modo estricto (`StrictUndefined`).
- **`ConfigSyntaxValidator` (`src/networking_agent/guardrails/syntax_validator.py`):** Motor de análisis estático en seco (*Dry-Run*):
  - Evalúa línea por línea antes de abrir sockets SSH.
  - Bloquea comandos destructivos (`reload`, `reboot`, `erase`, `zeroize`, `reset-configuration`).
  - Detecta variables Jinja2 huérfanas (`{{...}}`).
  - Audita el balance de llaves en Junos (`{...}`).
- **`BatchDeployer`:** Orquestador de despliegue sobre listas de dispositivos (`List[DeviceInventory]`) con transaccionalidad por equipo y reversión individualizada.

---

### 2.5. Capa de Controladores de Red Multi-Fabricante (`src/networking_agent/drivers/`)

- **`base.py` (`NetworkOSDriver`):**
  - **SSH Connection Pooling:** Mantiene una sesión SSH activa a lo largo del flujo completo, eliminando handshakes repetitivos y reduciendo el tiempo de ejecución en más de un 80%.
  - **Dynamic Management Discovery (`discover_active_management_interfaces`):** Inspecciona salidas de telemetría en vivo para identificar qué puerto físico sostiene la IP de conexión SSH o la ruta por defecto (`0.0.0.0/0`), previniendo caídas accidentales.
  - **Protocol Diagnostic Commands:** Métodos especializados (`_bgp_diag_commands`, `_ospf_diag_commands`, `_vlan_diag_commands`, `_stp_diag_commands`, `_channel_diag_commands`, `_acl_diag_commands`) para interrogación en caliente.
  - **Snapshot y Rollback:** Generación de respaldos locales en `backups/<host>_<timestamp>.cfg` con prevención de *path traversal*.
- **Controladores Específicos:**
  - `cisco_ios.py`: Cisco IOS y IOS-XE con guardado persistente (`save_config`).
  - `cisco_nxos.py`: Cisco NX-OS con sesiones atómicas (`configure session`) y checkpoints de hardware nativos.
  - `cisco_xr.py`: Cisco IOS-XR con confirmación temporizada (`commit confirmed 180`).
  - `juniper.py`: Juniper Junos con reversión automática (`commit confirmed 3`).
  - `mikrotik.py`: MikroTik RouterOS v6/v7 con snapshots binarios (`/system backup save`).

---

## 3. Modelo de Hilos y Concurrencia (*Threading Model*)

El sistema combina el bucle de eventos reactivo de Textual con hilos de trabajo asíncronos para garantizar fluidez absoluta en la interfaz:

```
[Textual Event Loop (Main Thread)] ── UI Render (60 FPS) & Key Events
               │
               ▼ (Lanza tarea pesada vía @work(thread=True))
[Worker Thread (Background)]        ── Netmiko SSH / LLM Request / Batch Engine
               │
               ▼ (Notifica progreso mediante TextualAgentObserver)
[Observer Bridge]                   ── safe_call() / call_from_thread()
               │
               ▼ (Actualiza widgets de forma thread-safe)
[UI Widgets Actualizados]          ── Log, Barras de Progreso, Status Card
```

### Protocolo Human-in-the-Loop en Concurrencia:
Cuando el agente requiere autorización del operador:
1. El hilo de trabajo ejecuta `observer.on_hitl_approval_required(...)`.
2. Se programa la apertura del modal en el hilo principal mediante `call_from_thread()`.
3. El hilo de trabajo se suspende en un `threading.Event().wait()`, **sin congelar el event loop de Textual**.
4. El operador revisa el diff y presiona `Y` o `N`.
5. El modal despierta al hilo de trabajo que continúa la ejecución de manera atómica.

---

## 4. Diagramas de Secuencia Operacionales

### 4.1. Secuencia: Troubleshooting Autónomo Closed-Loop

```mermaid
sequenceDiagram
    autonumber
    actor Operador as "👤 Operador NOC"
    participant TUI as "🖥️ TroubleshootingWorkspace"
    participant Agent as "🤖 NetworkAssistantAgent"
    participant Driver as "🔌 NetworkOSDriver (SSH Pool)"
    participant Brain as "🧠 AI Brain (Ollama/Gemini)"
    participant Guard as "🛡️ BlastRadiusGuard"
    participant Device as "🖧 Router Objetivo"

    Operador->>TUI: Selecciona equipo y redacta síntoma en lenguaje natural
    TUI->>Agent: execute_troubleshooting(device, symptom)
    
    rect rgb(240, 248, 255)
        Note over Agent,Device: Interrogación de Telemetría Dinámica
        Agent->>Driver: get_troubleshooting_commands(symptom)
        Driver-->>Agent: Lista de show commands especializados
        Agent->>Driver: run_diagnostic_interrogation(diag_cmds)
        Driver->>Device: show ip bgp / show interfaces / etc.
        Device-->>Driver: Estadísticas operativas en vivo
        Driver-->>Agent: Telemetría en bruto + active management interfaces
    end

    Agent->>Brain: analyze_event(telemetry_payload)
    Brain-->>Agent: NetworkIntent estructurado (Causa raíz + Severidad + Acción)
    Agent->>TUI: Muestra informe técnico de diagnóstico

    alt No Requiere Cambio
        Agent->>TUI: Incidente resuelto sin modificaciones (NO_OP)
    else Requiere Remediación
        Agent->>Guard: verify_intent(intent, wan_interfaces)
        alt Violación de Blast Radius
            Guard-->>Agent: BlastRadiusViolationError
            Agent->>TUI: Alerta roja de seguridad & Bloqueo
        else Aprobado por Guardarraíles
            Agent->>TUI: Solicita aprobación Human-in-the-Loop
            TUI-->>Operador: Muestra HitLModal con diff y rollback plan
            alt Operador Rechaza (N)
                Operador->>TUI: Rechazar (N)
                TUI-->>Agent: False
                Agent->>TUI: Operación cancelada & Auditada
            else Operador Aprueba (Y)
                Operador->>TUI: Autorizar (Y)
                TUI-->>Agent: True
                Agent->>Driver: take_snapshot()
                Driver->>Device: Captura running-config previa
                Agent->>Driver: execute_remediation(candidate_commands)
                Driver->>Device: Inyección de comandos CLI validados
                Agent->>Driver: verify_health()
                Driver->>Device: Comprobación post-cambio
                alt Verificación Exitosa
                    Agent->>Driver: save_config()
                    Agent->>TUI: Remediación exitosa confirmada
                else Verificación Fallida
                    Agent->>Driver: rollback(snapshot)
                    Agent->>TUI: Reversión automática ejecutada
                end
            end
        end
    end
```
