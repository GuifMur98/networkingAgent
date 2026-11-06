# 📋 Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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
