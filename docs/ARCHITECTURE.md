# 🏛️ Arquitectura del Sistema: NetworkingAgent Enterprise v2.0

> **Diseño Arquitectónico Hexagonal, Patrones de Ingeniería Closed-Loop y Garantías de Confiabilidad**

---

## 1. Visión General del Diseño

**NetworkingAgent Enterprise v2.0** está construido bajo el patrón de **Arquitectura Hexagonal (Puertos y Adaptadores)** combinado con automatización en **bucle cerrado (*Closed-Loop Automation*)**. 

El sistema desacopla de manera rigurosa tres responsabilidades fundamentales:
1. **Razonamiento Cognitivo:** Los Modelos de Lenguaje (LLMs) operan exclusivamente como motores de inferencia diagnóstica y síntesis lógica; **nunca** emiten comandos CLI directamente hacia los equipos sin pasar por esquemas tipados estritos (`NetworkIntent` o `ConfigurationIntent`).
2. **Defensa en Profundidad y Guardarraíles:** Ninguna instrucción generada por un operador o un modelo de IA alcanza el transporte SSH sin atravesar el análisis estático preventivo (`ConfigSyntaxValidator`), la validación de comandos prohibidos (`CommandValidator`) y la protección de interfaces de gestión y WAN (`BlastRadiusGuard`).
3. **Ejecución Transaccional Multi-Fabricante:** Los controladores de red (*drivers*) traducen intenciones lógicas a sintaxis nativa de fabricante, gestionan la reutilización de conexiones SSH (*Connection Pooling*), generan snapshots previos al cambio y garantizan la reversión atómica (*Rollback*) si la verificación operativa posterior detecta anomalías.

```mermaid
flowchart TD
    subgraph PresentationLayer ["1. Capa de Presentación e Interacción Reactiva"]
        TUI["Terminal UI Textual: 60 FPS Asíncrona"]
        CLI["Rich Wizard CLI Clásico"]
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

    subgraph AutomationLayer ["3. Capa de Automatización y Plantillas"]
        TE["TemplateEngine (Jinja2)"] --> SV["ConfigSyntaxValidator (Dry-Run)"]
        SV --> BD["BatchDeployer (Orquestador Multi-Host)"]
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

    subgraph ClosedLoopExecution ["6. Ejecución en Bucle Cerrado"]
        DRV --> SNAP["1. Snapshot Pre-Cambio (.cfg / Checkpoint)"]
        SNAP --> EXEC["2. Inyección Transaccional CLI"]
        EXEC --> POST["3. Verificación Post-Cambio (Health / Diag)"]
        POST -->|Éxito| AUD["Auditoría Inmutable: SUCCESS"]
        POST -->|Fallo| RBK["Rollback Inmediato a Snapshot"]
        RBK --> AUD_FAIL["Auditoría Inmutable: ROLLBACK"]
    end
```

---

## 2. Capas del Sistema y Componentes

### 2.1. Capa de Presentación Reactiva (`src/networking_agent/tui/`)

La interfaz de usuario principal está construida con el framework reactivo **Textual**:

- **`app.py` (`NetworkingAgentApp`):** Controlador principal de la aplicación.
  - Orquesta el montaje y conmutación entre las 5 vistas de la plataforma sin recargas destructivas de pantalla.
  - Ejecuta operaciones de larga duración (SSH de Netmiko, consultas LLM, validación estática y despliegues en lote) en hilos de trabajo asíncronos en segundo plano utilizando el decorador `@work(thread=True)`, garantizando que la interfaz nunca se congele.
  - Proporciona insignias de telemetría dinámica en el encabezado (`BRAIN`, `EQUIPOS`, `HITL`) y escucha atajos globales (`1-5`, `h`, `s`, `d`, `r`, `q`).
- **Vistas Especializadas (`src/networking_agent/tui/widgets/`):**
  - `TroubleshootingView`: Diagnóstico por síntomas en lenguaje natural, selección de router y visualización del informe técnico de causa raíz.
  - `ConfigurationView`: Formulario declarativo para aprovisionamiento multi-protocolo, selector de categoría y visor de candidate CLI diff.
  - `AutomationView`: Editor de plantillas `TextArea` con números de línea, selector de templates Jinja2, botón de validación dry-run y selector múltiple de equipos (`SelectionList`).
  - `InventoryView`: Tabla de gestión de routers y switches con ejecución de pruebas de conectividad SSH en vivo.
  - `AuditView`: Visor en tiempo real de la bitácora inmutable JSONL.
- **Ventanas Modales Flotantes (`src/networking_agent/tui/modals/`):**
  - `AIOptionsModal`: Configuración adaptativa de proveedor y modelo LLM con enmascaramiento dinámico de contraseñas.
  - `DeviceModal`: Formulario de alta de dispositivos con validación de IP/Host y cifrado automático de credenciales.
  - `HitLApprovalModal`: Compuerta interactiva de confirmación humana con previsualización de comandos exactos a inyectar y detalles de rollback.

---

### 2.2. Capa Cognitiva Multi-Cerebro (`src/networking_agent/brains/`)

- **`base.py` (`LLMBrain`):** Interfaz abstracta que define los dos contratos de inferencia:
  1. `analyze_event(telemetry_data: str) -> NetworkIntent`: Diagnóstico de incidentes y selección de acción remediadora.
  2. `synthesize_configuration(device_host, vendor_family, natural_request, protocol_hint) -> ConfigurationIntent`: Síntesis declarativa de configuración multi-protocolo.
  - Protege las entradas no confiables mediante delimitadores XML `<telemetry_event>` y directivas en `HARDENED_SYSTEM_PROMPT` y `HARDENED_CONFIG_SYSTEM_PROMPT`.
- **`ollama.py`:** Conector local y soberano que interactúa con el endpoint HTTP de Ollama utilizando salidas estructuradas en formato JSON (`format="json"`).
- **`gemini.py`:** Conector oficial utilizando el nuevo SDK `google-genai` para invocar modelos `gemini-2.5-pro` y `gemini-2.5-flash` con forzado estricto de esquema Pydantic (`response_schema`).
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

### 2.4. Capa de Automatización y Despliegue en Lote (`src/networking_agent/engine/automation.py`)

- **`TemplateEngine`:** Gestiona el catálogo de plantillas pre-cargadas (Hardening, VLAN/SVI, OSPF, NTP/Syslog, Junos IRB) y compila plantillas Jinja2 en modo estricto (`StrictUndefined`) para evitar variables indefinidas silenciosas.
- **`ConfigSyntaxValidator` (`src/networking_agent/guardrails/syntax_validator.py`):** Motor de análisis estático en seco (*Dry-Run*):
  - Evalúa línea por línea antes de abrir sockets SSH.
  - Bloquea comandos de reinicio (`reload`, `reboot`, `system reboot`).
  - Bloquea comandos destructivos de almacenamiento (`format flash:`, `erase startup-config`, `write erase`, `zeroize`, `reset-configuration`).
  - Detecta variables de plantilla sin renderizar (`{{...}}`).
  - Audita el balance de bloques jerárquicos en Junos (`{...}`).
  - Verifica prefijos requeridos en MikroTik RouterOS (`/` o `:`).
- **`BatchDeployer`:** Orquestador de despliegue sobre listas de dispositivos (`List[DeviceInventory]`):
  - Aplica validación estática previa.
  - Itera sobre cada equipo realizando un snapshot pre-cambio individual.
  - En caso de error en un equipo específico, ejecuta un rollback aislado sobre ese equipo sin abortar ni afectar a los dispositivos que completaron exitosamente.
  - Genera un reporte inmutable [`BatchDeploymentResult`](../src/networking_agent/models/config_intent.py).

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

## 3. Diagramas de Secuencia Operacionales

### 3.1. Secuencia: Troubleshooting Autónomo Closed-Loop

```mermaid
sequenceDiagram
    autonumber
    actor Operador as "👤 Operador NOC"
    participant TUI as "🖥️ TroubleshootingView"
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
            Agent->>Driver: build_candidate_commands(intent)
            Driver-->>Agent: Comandos CLI nativos
            Agent->>TUI: Despliega Modal HitL con Diff CLI y Rollback
            TUI->>Operador: ¿Autoriza el cambio? [s/n]
            
            alt Operador Rechaza
                Operador-->>TUI: Rechazado (n)
                Agent->>TUI: Remediación abortada (OPERATOR_REJECTED)
            else Operador Autoriza
                Operador-->>TUI: Autorizado (s)
                
                rect rgb(255, 250, 240)
                    Note over Agent,Device: Snapshot & Ejecución Transaccional
                    Agent->>Driver: backup_running_config()
                    Driver->>Device: Descarga snapshot a backups/<host>.cfg
                    Agent->>Driver: execute_commands(candidate_cli)
                    Driver->>Device: Inyecta configuración saneada
                end

                rect rgb(240, 255, 240)
                    Note over Agent,Device: Verificación Post-Cambio
                    Agent->>Driver: run_health_check()
                    Driver->>Device: Re-interroga estado operativo
                    alt Verificación Exitosa
                        Agent->>TUI: [OK] Remediación verificada con éxito
                    else Verificación Fallida
                        Agent->>Driver: rollback(backup_file)
                        Driver->>Device: Restaura configuración original previa
                        Agent->>TUI: [FALLO] Rollback automático ejecutado
                    end
                end
            end
        end
    end
```

---

### 3.2. Secuencia: Configuración Declarativa Multi-Protocolo

```mermaid
sequenceDiagram
    autonumber
    actor Operador as "👤 Operador de Red"
    participant TUI as "🖥️ ConfigurationView"
    participant Agent as "🤖 NetworkAssistantAgent"
    participant Brain as "🧠 AI Brain"
    participant Validator as "🛡️ ConfigSyntaxValidator"
    participant Driver as "🔌 NetworkOSDriver"
    participant Device as "🖧 Switch / Router"

    Operador->>TUI: Describe solicitud (ej. BGP Peering, OSPF, VLAN)
    TUI->>Agent: execute_configuration(device, request, protocol_hint)
    
    Agent->>Brain: synthesize_configuration(device, request)
    Brain-->>Agent: ConfigurationIntent (candidate_cmds, verif_cmds, rollback_cmds)
    
    Agent->>Validator: validate_script(candidate_cmds)
    alt Error Sintáctico / Comando Destructivo
        Validator-->>Agent: is_valid = False
        Agent->>TUI: Alerta de validación sintáctica & Cancela
    else Sintaxis Válida
        Validator-->>Agent: is_valid = True (clean_commands)
        Agent->>TUI: Despliega Modal HitL con Diff de Configuración
        TUI->>Operador: Confirmación de despliegue [s/n]
        
        alt Aprobado por el Operador
            Agent->>Driver: backup_running_config()
            Driver->>Device: Guarda snapshot pre-cambio
            Agent->>Driver: execute_commands(candidate_cmds)
            Driver->>Device: Aplica configuración nativa
            
            opt Comandos de Verificación Presentes
                Agent->>Driver: Ejecuta verification_commands (show)
                Driver->>Device: show ip bgp summary / etc.
                Device-->>Driver: Estado post-configuración
            end
            
            Agent->>TUI: Configuración completada y auditada exitosamente
        end
    end
```

---

### 3.3. Secuencia: Despliegue en Lote con `BatchDeployer`

```mermaid
sequenceDiagram
    autonumber
    actor Operador as "👤 Ingeniero de Automatización"
    participant TUI as "🖥️ AutomationView (Editor)"
    participant Deployer as "⚙️ BatchDeployer"
    participant Validator as "🛡️ ConfigSyntaxValidator"
    participant Driver as "🔌 NetworkOSDriver"
    participant Target as "🖧 Equipos [Host 1 ... Host N]"

    Operador->>TUI: Escribe/Modifica plantilla Jinja2 y selecciona equipos
    Operador->>TUI: Clic en 'Validar Sintaxis (Dry-Run)'
    TUI->>Validator: validate_script(raw_text)
    Validator-->>TUI: SyntaxValidationReport (Líneas evaluadas, errores, advertencias)
    
    Operador->>TUI: Clic en 'Desplegar en Equipos'
    TUI->>Deployer: deploy_to_devices(selected_devices, script)
    
    loop Para cada equipo en la selección
        Deployer->>Driver: get_os_driver(device)
        Deployer->>Driver: backup_running_config()
        Driver->>Target: Descarga snapshot individual (.cfg)
        
        Deployer->>Driver: execute_commands(clean_commands)
        alt Inyección Exitosa
            Driver->>Target: Inyecta comandos CLI
            Deployer->>Deployer: device_results[host] = SUCCESS
        else Fallo durante Inyección
            Deployer->>Driver: rollback(backup_path)
            Driver->>Target: Restaura snapshot original
            Deployer->>Deployer: device_results[host] = FAILED (Rollback Aplicado)
        end
        Deployer->>Driver: disconnect()
    end

    Deployer-->>TUI: BatchDeploymentResult (Resumen de éxitos y fallos aislados)
```
