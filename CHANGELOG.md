# 📋 Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.1.1] - 2026-11-08

### 🛡️ Ciberseguridad y Remediación de Auditoría de Penetración (Security)
- **Remediación Integral de 8 Hallazgos de Seguridad (Ethical Hacking & Pentest):**
  - **VULN-01 (SSTI a RCE en Jinja2):** Implementación de `HardenedSandboxedEnvironment` en `engine/automation.py`, bloqueando acceso a atributos dunder (`__class__`, `__globals__`, `__mro__`, etc.) y callables peligrosos (`eval`, `popen`, etc.).
  - **VULN-02 (Aceptación ciega de llaves SSH / MitM):** Carga forzosa del almacén `known_hosts` del sistema (`system_host_keys=True`) en `to_netmiko_dict()`, detección de discrepancias de llaves (`BadHostKeyException`) con interrupción inmediata y emisión de alerta crítica de seguridad. Soporte para `ssh_strict=True`.
  - **VULN-03 (Evasión de guardarraíles):** Ampliación de listas negras en `CommandValidator` y `ConfigSyntaxValidator` para vetar transferencias TFTP/FTP/HTTP (`copy tftp:`, `tool fetch`), comunidades SNMP RW (`snmp-server community <name> RW`), degradación a Telnet (`transport input telnet`), desvíos de ruta por defecto (`0.0.0.0/0`), deshabilitación de cifrado de contraseñas (`no service password-encryption`) y shells del SO (`guestshell`, `start shell`).
  - **VULN-04 (Permisos ineficaces de llave maestra en Windows):** Restricción estricta de DACLs en `core/crypto.py` (`secure_file_permissions`), deshabilitando herencia NTFS y asignando control total exclusivamente al usuario actual (`icacls /inheritance:r /grant:r "%USERNAME%:(F)"`) y `0600` en sistemas POSIX.
  - **VULN-05 (CWD Hijacking y confusión de rutas):** Anclaje determinista de directorios con `get_app_data_dir()` y `get_app_log_dir()` con variable prioritaria `NETWORKING_AGENT_DATA_DIR` y fallback a `%LOCALAPPDATA%\NetworkingAgent\data`. Integración de cambio de directorio previo en lanzadores.
  - **VULN-06 (Filtración de credenciales en logs de auditoría):** Sanitización universal de datos confidenciales (`mask_sensitive_data()`) en `core/audit.py` antes de registrar comandos o respuestas CLI en `audit.jsonl`.
  - **VULN-07 (Encadenamiento criptográfico continuo SHA-256):** Implementación de hash encadenado (`prev_hash` + `event_hash`) en cada entrada de `AuditLogger` con verificación matemática de inmutabilidad mediante `verify_audit_integrity()`.
  - **VULN-08 (Instaladores seguros):** Eliminación de tuberías directas a intérpretes de shell (`curl | sh` / `irm | iex`), migrando a un patrón seguro de descarga en dos pasos a archivos temporales aislados con comprobación de integridad.

### 🎨 Ergonomía Visual y Soporte Integral de Tema Claro (Added)
- **Tema Oficial Claro Suave (`agent-light`):**
  - Paleta ergonómica basada en tonos zinc y pizarra suave (`#f8fafc` fondo general, `#ffffff` superficie de tarjetas, `#1e293b` tipografía oscura contrastada, `#cbd5e1` / `#0369a1` bordes sutiles, acentos verde esmeralda y ámbar cálido).
  - Diseñado específicamente para eliminar fatiga visual y reflejos excesivos en ambientes luminosos.
- **Tema Oficial Cyberpunk NOC (`agent-dark`):**
  - Consola de centro de operaciones con fondo azul espacial profundo (`#0a0f1d`), superficie grafito (`#111827`) y acentos cian eléctrico (`#00e5ff`) y oro (`#fbbf24`).
- **Corrección de Fondo de Tarjetas en Dashboard:**
  - Corrección de `.home-nav-card` y `HomeNavCard` para respetar dinámicamente `$surface` y `$foreground`, eliminando los fondos negros fijos que persistían en tema claro.
  - Dinamización de bordes, indicadores ASCII y gráficos de estado en los 5 módulos para armonizar con el tema activo.
- **Comandos Rápidos en Paleta (`Ctrl+P`):**
  - Acciones dedicadas: `Tema: Modo Claro Suave (agent-light)` y `Tema: Modo Oscuro Cyberpunk (agent-dark)`.

### 🧪 Suite de Pruebas Automatizadas Ampliada (Changed)
- Cobertura expandida de 172 a **189 pruebas automatizadas** (`pytest tests/`) con 100% de éxito en todos los sistemas operativos.
- Nuevos tests de seguridad (`tests/test_security_audit_remediation.py`) y ergonomía de temas (`test_agent_light_theme_and_color_ergonomics`).

---

## [2.1.0] - 2026-11-08

### 🚀 Paleta de Comandos, Temas Visuales y Operaciones Globales (Added)
- **Paleta de Comandos Depurada y Selector de Temas Visuales (`Ctrl+P` / `F1`):**
  - Rediseño centrado exclusivamente en operaciones del sistema, temas y navegación global, eliminando acciones redundantes que ya contaban con botones dedicados en pantalla.
  - **Selector de más de 20 Temas Visuales (`change_theme`):** Integración nativa de la biblioteca de paletas de Textual (Nord, Dracula, Tokyo Night, Gruvbox, Catppuccin, Monokai, Solarized, etc.).
  - **Persistencia en Base de Datos:** El tema elegido se guarda automáticamente en SQLite (`app_theme`) y se restaura sin pérdida de configuración entre reinicios de la aplicación.
  - **Conmutador Modo Oscuro / Claro (`toggle_dark`)** y acción de restauración a valores corporativos de fábrica (`reset_theme`).
  - **Captura Vectorial de Pantalla SVG (`screenshot`):** Herramienta integrada para capturar y exportar la vista actual de la terminal a formato SVG en `logs/screenshot_<timestamp>.svg`.
  - Catálogo depurado a 18 comandos de alto valor operativo sin emojis ni iconos decorativos, respetando los estándares de diseño corporativo NOC / Mission Control.
  - Indicador de acceso rápido `^p Paleta` anclado de forma fija en la esquina inferior derecha del Dashboard de Inicio.

### 🖧 Diagnóstico de Conectividad en Tiempo Real (Added)
- **Motor de Verificación de Red (`engine/connectivity.py`):**
  - Implementación de pruebas asíncronas de **Ping ICMP** con medición precisa de latencia de ida y vuelta (RTT) en milisegundos y cálculo de tasa de éxito/pérdida de paquetes.
  - Prueba de disponibilidad de servicio **SSH (TCP 22)** mediante conexión de socket no invasiva, previniendo intentos de conexión fallidos antes de invocar Netmiko.
  - Integración en la tabla del Módulo de Inventario (`DeviceInventoryView`) mediante botones de acción directa: `Hacer Ping (ICMP)`, `Probar Conexión (SSH)` y `Test Completo`.

### ⚡ Asistente de Plantillas Jinja2 y Variables Dinámicas (Added)
- **Guía Interactiva de Parámetros en Modal de Plantillas (`TemplateModal`):**
  - Panel visual de referencia rápida para la sintaxis de variables dinámicas Jinja2 (`{{ nombre_variable }}`).
  - Botones tipo chip clickeables para inserción automática en el cursor de variables de uso frecuente (`vlan_id`, `vlan_name`, `ip_address`, `netmask`, `gateway`, `interface`, `description`, `bgp_as`).
  - Botón **Detectar Variables** para analizar el contenido CLI del script y confirmar al operador los parámetros parametrizados reconocidos por el motor de automatización.
  - Ajustes ergonómicos de espaciado y márgenes visuales para evitar solapamientos con la barra de desplazamiento.

### 🛡️ Auditoría Forense y Gestión de Bitácora (Added)
- **Herramientas de Exportación y Limpieza de Auditoría (`AuditTableWidget`):**
  - Botón **Exportar JSON** para volcar el historial de operaciones forenses (con hashes criptográficos SHA-256) en archivos JSON estructurados para integración con sistemas SIEM.
  - Botón **Purgar Tests** con cuadro de diálogo de confirmación de seguridad para eliminar eventos de prueba generados por ejecuciones sintéticas o de desarrollo, manteniendo intactos los registros de producción.
  - Filtrado reactivo en caliente por equipo y por resultado operacional (`ALL`, `SUCCESS`, `FAILED`, `ROLLBACK`, `BLOCKED`).

### 📦 Empaquetado, Instaladores y Despliegue Empresarial (Added)
- **Instaladores Automatizados y Paquetes Standalone:**
  - Creación de [`install.ps1`](install.ps1): instalador inteligente para Windows con soporte dual (código fuente y binario compilado), registro automático en el `PATH` del usuario y generación de accesos directos en el Escritorio y Menú Inicio.
  - Creación de [`install.sh`](install.sh): instalador para Linux y macOS con enlace simbólico en `~/.local/bin/` y actualización automática de `.bashrc` o `.zshrc`.
  - Especificación [`networking_agent.spec`](networking_agent.spec): empaquetado PyInstaller con inclusión automática de los 236 submódulos de Textual (controladores `windows_driver`, `linux_driver`) y 270 submódulos de Netmiko (`ntc_templates`).
  - Herramienta de compilación [`scripts/build_standalone.py`](scripts/build_standalone.py): generación automatizada de paquetes `.zip` (Windows) y `.tar.gz` (Linux) que incorporan `instalar.bat` (instalador de 1 clic) e `iniciar.bat` (lanzador portable).
  - Publicación de la **Guía Definitiva de Instalación y Despliegue** ([`docs/INSTALLATION_GUIDE.md`](docs/INSTALLATION_GUIDE.md)).

### ⌨️ Ergonomía y Navegación Contextual (Changed)
- **Indicadores de Atajos en Botones:**
  - Actualización de todos los botones con atajo asignado para reflejar la tecla entre paréntesis: `Volver al Inicio (h)`, `+ Registrar Equipo (d)`, `Recargar (r)`, `Cancelar (Esc)`, `Cerrar (Esc)`, `Autorizar y Aplicar (Y)`, `Rechazar y Abortar (N)`.
- **Filtrado Dinámico de Pie de Página:**
  - En los 5 módulos operacionales, el único atajo visible en el pie de página es `h Inicio`, reduciendo distracciones y evitando activaciones accidentales.
  - En el Dashboard de Inicio se visualizan todos los atajos generales a la izquierda (`h`, `q`, `d`, `s`, `r`) y la Paleta de Comandos a la derecha (`^p`).

### 🧪 Calidad y Pruebas Automatizadas (Changed)
- **Suite de Pruebas Ampliada:** La cobertura creció de 125 a **172 pruebas automatizadas** (`pytest`) con 100% de aprobación.
- **Nuevas Pruebas Unitarias y de Integración:**
  - `tests/test_connectivity.py`: Pruebas de Ping, comprobación de socket TCP 22 e interacción en la TUI de inventario.
  - `tests/test_command_palette.py`: Pruebas de catálogo, búsqueda difusa, ausencia de emojis, apertura de la paleta y anclaje inferior derecho.
  - `tests/test_audit_table.py`: Pruebas de renderizado de tabla, filtros, exportación JSON y purga de registros de prueba.
  - `tests/test_conflict_analyzer.py`: Pruebas de detección de colisión de subredes y solapamientos IP.

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
  - Modal dinámico de Configuración de IA (`VaultModal` / `AIOptionsModal`): actualización en tiempo real de campos, etiquetas, enmascaramiento y modelos sugeridos según el proveedor seleccionado (Ollama, Gemini, OpenAI, Claude).
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
