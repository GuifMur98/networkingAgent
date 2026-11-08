# 🚀 NetworkingAgent Enterprise v2.1.1 - Release Notes

**Fecha de Lanzamiento:** 8 de Noviembre de 2026  
**Etiqueta de Versión:** `v2.1.1`  
**Licencia:** Apache 2.0  
**Certificación:** Python 3.14 / Textual TUI v2.1  
**Estado de Pruebas:** 194/194 aprobadas (100% passing)  

---

## 🌟 Resumen Ejecutivo

**NetworkingAgent Enterprise v2.1.1** es una actualización de estabilidad, seguridad y ergonomía visual que consolida el asistente autónomo de ingeniería de redes. Esta versión incorpora la remediación completa de los **8 hallazgos identificados en la auditoría ética de ciberseguridad**, el rediseño ergonómico del **Modo Claro Suave (`agent-light`)**, la corrección definitiva del renderizado de fondo en tarjetas de navegación, y la ampliación de la suite de pruebas a **194 tests automatizados** (100% aprobados).

---

## 🛡️ Ciberseguridad y Remediaciones del Pentest

Tras someter el sistema a un test de penetración exhaustivo, se resolvieron e integraron las siguientes defensas en profundidad:

1. **🔴 VULN-01: Sandbox Estricto contra Inyección de Plantillas (SSTI en Jinja2):**
   - Se implementó `HardenedSandboxedEnvironment` en `engine/automation.py`, vetando atributos dunder (`__class__`, `__mro__`, `__globals__`, etc.) y llamadas a funciones de sistema (`eval`, `popen`, `exec`), impidiendo cualquier escape hacia ejecución de código (RCE).
2. **🔴 VULN-02: Transporte SSH Inmune a Man-in-the-Middle (MitM):**
   - Netmiko activa forzosamente `system_host_keys=True` para cargar el almacén `known_hosts` del sistema. Se captura `BadHostKeyException` emitiendo una alerta crítica inmediata ante suplantación de identidad del router. Soporte para `ssh_strict=True`.
3. **🟠 VULN-03: Ampliación de Listas Negras de Comandos y Sintaxis:**
   - Blindaje en `CommandValidator` y `ConfigSyntaxValidator` contra transferencias no autorizadas (`copy tftp:`, `tool fetch`), comunidades SNMP con permisos de escritura (RW), degradación a Telnet, inyecciones de default routes (`0.0.0.0/0`) y shells de sistema.
4. **🟠 VULN-04: Permisos Estrictos en Llave Maestra (Windows NTFS DACLs & POSIX):**
   - En Windows, `secure_file_permissions` elimina la herencia de permisos NTFS y restringe acceso total exclusivamente al usuario actual con `icacls /inheritance:r /grant:r "%USERNAME%:(F)"`. En POSIX aplica permisos `0600`.
5. **🟠 VULN-05: Aislamiento contra Secuestro de Directorio de Trabajo (CWD Hijacking):**
   - Anclaje determinista de rutas mediante `get_app_data_dir()` hacia `%LOCALAPPDATA%\NetworkingAgent\data` y cambio automático de directorio en lanzadores.
6. **🟡 VULN-06: Sanitización Universal de Credenciales en Auditoría:**
   - Enmascaramiento preventivo con `mask_sensitive_data()` para contraseñas, secretos y tokens en comandos y respuestas antes de persistir en `audit.jsonl`.
7. **🟡 VULN-07: Encadenamiento Criptográfico Continuo SHA-256 en Auditoría:**
   - Cada registro incluye `prev_hash` y `event_hash` con función de validación de integridad `verify_audit_integrity()`.
8. **🟡 VULN-08: Instaladores Seguros en Dos Pasos:**
   - Se eliminaron las tuberías ciegas a shell (`curl | sh` / `irm | iex`), migrando a descargas en dos pasos a archivos temporales aislados con verificación previa.

---

## 🎨 Ergonomía Visual y Rediseño de Tema Claro

- **Tema Oficial `agent-light` (Modo Claro Suave):**
  - Paleta pensada para turnos prolongados de trabajo en entornos muy iluminados: fondo zinc suave (`#f8fafc`), superficie `#ffffff`, texto contrastado `#1e293b`, bordes pizarra `#cbd5e1` / `#0369a1`, sin blancos deslumbrantes.
- **Corrección de Fondo de Tarjetas en Dashboard:**
  - `HomeNavCard` y `.home-nav-card` adaptan su fondo a `$surface` y su texto a `$foreground`, eliminando los bloques oscuros que persistían en modo claro.
- **Dinamización de Colores en Todos los Módulos:**
  - Adaptación automática de indicadores ASCII, bordes redondeados y gráficos en Troubleshooting, Configuración, Inventario y Auditoría.
- **Acceso Rápido en Paleta de Comandos (`Ctrl+P`):**
  - Comandos directos para alternar entre `agent-light` y `agent-dark`.

---

## 📊 Métricas de Calidad

- **Total de Pruebas Automatizadas:** **194 pruebas** (`pytest tests/`) con 100% de éxito.
- **Linter y Formato:** 0 errores con `ruff check .`
- **Compatibilidad de Plataformas:** Windows 10/11 x64, Linux x64 (Ubuntu, Debian, RHEL, Arch), macOS (Apple Silicon e Intel).

---

## ⚡ Descarga e Instalación

### 📦 1. Binarios Precompilados Standalone (Sin Python)
- **`networking-agent-v2.1.1-windows-x64.zip` (Windows x64):**
  - Doble clic en `instalar.bat` para registrar en PATH y crear accesos directos.
  - Doble clic en `iniciar.bat` para modo portable.

### 📥 2. Instalador Automatizado por Terminal (Patrón Seguro en 2 Pasos)
- **Windows (PowerShell):**
  ```powershell
  Invoke-WebRequest -Uri https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.ps1 -OutFile "$env:TEMP\install.ps1"
  & "$env:TEMP\install.ps1"
  ```
- **Linux / macOS (Bash):**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
  ```
