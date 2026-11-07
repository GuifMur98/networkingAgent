# 📋 Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.0.0] - 2026-11-06

### 🚀 Evolución Mayor de Arquitectura y Modos Operativos (Added)
- **Tres Pilares Operativos de Ingeniería de Red:**
  - **Pilar 1: Modo Troubleshooting:** Diagnóstico autónomo y análisis de causa raíz en lenguaje natural con interrogación de telemetría multi-fabricante en vivo, correlación L1-L7, guardarraíl de blast radius y compuerta Human-in-the-Loop (HitL).
  - **Pilar 2: Modo Configuración Declarativa:** Aprovisionamiento asistido en lenguaje natural para protocolos críticos (BGP, OSPF, EIGRP, STP, Port-Channel, VLANs, ACLs, Servicios NTP/DNS/Syslog). Síntesis estructurada mediante `ConfigurationIntent`, cálculo de previsualización diferencial (*candidate CLI diff*), comandos de verificación post-despliegue y reversión atómica.
  - **Pilar 3: Modo Automatización & Despliegue en Lote:** Editor de texto integrado `TextArea` con numeración de líneas, catálogo de plantillas Jinja2 parametrizadas, validador de sintaxis en seco (*dry-run*) `ConfigSyntaxValidator` y orquestador multi-dispositivo `BatchDeployer` con snapshots previos y rollback automático individualizado por equipo.
- **Modernización y Rediseño Completo de la TUI (Textual):**
  - Acceso directo a los 5 pilares operativos mediante botones numéricos `[1-5]` y atajos de teclado globales (`1-5`, `h` Inicio, `q` Salir, `d` Nuevo Equipo, `s` Ajustes IA, `r` Recargar).
  - Encabezado ultra-limpio con insignias de telemetría en tiempo real (`BRAIN`, `EQUIPOS`, `HITL`), eliminando títulos redundantes y pestañas que restaban espacio vertical.
  - Modal dinámico de Configuración de IA (`AIOptionsModal`): actualización en tiempo real de campos, etiquetas, enmascaramiento y modelos sugeridos según el proveedor seleccionado (Ollama, Gemini, OpenAI, Claude).
  - Solución total de recorte (*clipping*) en barras de botones y contenedores de herramientas mediante alturas CSS adaptativas (`height: 4` en barras de navegación, `height: 5` en barra de automatización).
  - Ancho de barra lateral garantizado (`width: 32`) en inventarios y selectores de equipo, evitando desplazamientos involuntarios fuera de la pantalla.
  - Eliminación de botones redundantes de retorno en las vistas secundarias.
- **Guardarraíles de Sintaxis y Seguridad Pre-Flight (`ConfigSyntaxValidator`):**
  - Análisis estático preventivo antes de tocar cualquier socket SSH.
  - Detección y bloqueo estricto de comandos destructivos (`reload`, `reboot`, `erase startup-config`, `write erase`, `zeroize`, `reset-configuration`).
  - Detección de variables Jinja2 sin renderizar (`{{...}}`, `{%...%}`) para prevenir inyección de texto malformado en terminales de producción.
  - Validación de paridad y balance de bloques jerárquicos en Juniper Junos (`{...}`).
  - Verificación de formato y prefijos obligatorios en MikroTik RouterOS (`/` o `:`).
- **Controladores de Red Multi-Fabricante Ampliados:**
  - Métodos de diagnóstico dinámico por síntoma (`get_troubleshooting_commands`).
  - Interrogación especializada por protocolo (`_bgp_diag_commands`, `_ospf_diag_commands`, `_vlan_diag_commands`, `_stp_diag_commands`, `_channel_diag_commands`, `_acl_diag_commands`) en Cisco IOS/XE, Cisco NX-OS, Juniper Junos y MikroTik RouterOS.
  - Verificación post-despliegue automatizada (`get_protocol_verification_commands`).
- **Pruebas y Calidad de Código:**
  - Suite de pruebas unitarias ampliada de 105 a **125 pruebas automatizadas**, con 100% de éxito (`pytest`).
  - Cobertura de tests para validación de sintaxis, modelos de configuración, plantillas Jinja2, orquestador en lote y componentes de la TUI.
  - Cero advertencias de linting (`ruff check`).

---

## [0.1.0] - 2026-11-05

### ✨ Características Nuevas (Added)
- **Soporte Multi-Fabricante Completo:**
  - Driver para Cisco IOS y IOS-XE.
  - Driver para Cisco NX-OS con sesiones atómicas (`configure session`) y checkpoints nativos.
  - Driver para Cisco IOS-XR con commit confirmado (`commit confirmed 180`).
  - Driver para Juniper Junos con reversión temporal (`commit confirmed 3`).
  - Driver para MikroTik RouterOS v6 y v7 con respaldo de sistema binario (`/system backup save`).
- **Arquitectura Multi-Cerebro Desacoplada:**
  - Integración nativa y privada con Ollama (`netexpert:latest`, autodescubrimiento).
  - Integración oficial con Google Gemini (`google-genai` para `gemini-2.5-pro` y `gemini-2.5-flash`).
  - Conectores para OpenAI (GPT-4o) y Anthropic Claude 3.5 Sonnet.
- **Modos de Diagnóstico Proactivo y Reactivo:**
  - Modo Proactivo: Interrogación en caliente de estado físico, errores de interfaz y CPU ante síntomas en lenguaje natural reportados por el operador.
  - Modo Reactivo: Ingesta de telemetría y logs de syslog.
- **Protección de Enlaces Críticos y Blast Radius:**
  - Descubrimiento dinámico de interfaces de administración remota (`discover_active_management_interfaces`).
  - Blindaje incondicional contra reinicios o apagados de interfaces WAN, uplinks y puertos de gestión.
- **Validación HitL Robusta:**
  - Interfaz interactiva de repregunta continua ante errores tipográficos accidentales sin cancelar la sesión.
- **Optimización de Rendimiento:**
  - Agrupación y reutilización de sesiones SSH (*SSH Connection Pooling*), reduciendo la latencia de 15s a <2s.
- **Bóveda Criptográfica en SQLite:**
  - Almacenamiento cifrado con Fernet (AES-128-CBC) con clave maestra blindada en permisos `0600`.
  - Base de datos SQLite optimizada con `PRAGMA journal_mode = WAL;`.
- **Suite de Pruebas y CI/CD:**
  - 105 pruebas unitarias automatizadas con `pytest`.
  - Workflows de GitHub Actions para CI multi-OS (Linux/Windows) y escaneo de seguridad.

### 🛡️ Seguridad (Security)
- Aislamiento estricto de telemetría contra *Indirect Prompt Injection* mediante delimitadores XML y reglas en `HARDENED_SYSTEM_PROMPT`.
- Validador `CommandValidator` reforzado contra inyección shell (`&&`, `|`, `;`, `\`), scripts persistentes y proxies no autorizados.
- Prevención de *Path Traversal* en nombres de host y generación de backups.
- Límite de 30,000 caracteres y purga de bytes nulos en telemetría para prevención de DoS.
