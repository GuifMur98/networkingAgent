# 🚀 NetworkingAgent Enterprise v2.1.0 - Release Notes

**Fecha de Lanzamiento:** 8 de Noviembre de 2026  
**Etiqueta de Versión:** `v2.1.0`  
**Licencia:** Apache 2.0  
**Certificación:** Python 3.14 / Textual TUI v2.1  
**Estado de Pruebas:** 172/172 aprobadas (100% passing)  

---

## 🌟 Resumen Ejecutivo

**NetworkingAgent Enterprise v2.1.0** representa la evolución más sólida y madura del asistente de ingeniería de redes autónomo en bucle cerrado (*Closed-Loop Automation*). Esta versión consolida una consola de terminal reactiva de alto rendimiento (`Textual TUI`) bajo una estética sobria *Cyberpunk NOC Mission Control*, incorporando una **Paleta de Comandos profesional**, **pruebas de conectividad en tiempo real (Ping ICMP y Socket SSH)**, un **asistente de plantillas Jinja2 con detección de variables** y un **módulo forense de auditoría inmutable con hashes SHA-256**.

---

## 📋 Novedades Destacadas

### 1. ⌨️ Paleta de Comandos Profesional (`Ctrl+P`)
- **Acceso Global:** Acceso instantáneo con `Ctrl+P` o mediante el botón `^p Paleta` anclado en la esquina inferior derecha del Dashboard de Inicio.
- **Búsqueda Difusa (*Fuzzy Search*):** Más de 15 operaciones técnicas indexadas para ejecutar diagnósticos, navegar entre módulos o cambiar modos de seguridad sin tocar el ratón.
- **Estándar NOC Corporativo:** Cero emojis e iconos decorativos, priorizando etiquetas técnicas de alta densidad.

### 2. 🖧 Diagnóstico de Conectividad en Tiempo Real (Módulo 4)
- **Prueba de Ping ICMP:** Medición en vivo de latencia de ida y vuelta (RTT) y porcentaje de paquetes recibidos utilizando subprocesos asíncronos nativos.
- **Validación de Socket SSH (TCP 22):** Comprobación no invasiva de accesibilidad del demonio SSH antes de iniciar conexiones Netmiko.
- **Test Completo:** Diagnóstico combinado Ping + SSH con dictamen consolidado para cada router o switch del inventario.

### 3. ⚡ Asistente de Plantillas Jinja2 y Variables Dinámicas (Módulo 3)
- **Guía Didáctica de Variables:** Panel interactivo explicativo sobre sintaxis de doble llave `{{ nombre_variable }}`.
- **Chips Rápidos de Inserción:** Inserción en la posición del cursor de parámetros frecuentes (`vlan_id`, `vlan_name`, `ip_address`, `netmask`, `gateway`, `interface`, `description`, `bgp_as`).
- **Botón Detectar Variables:** Escaneo automático del texto CLI para confirmar las variables dinámicas reconocidas en la plantilla.
- **Validación Pre-Flight:** Análisis estático preventivo (`ConfigSyntaxValidator`) adaptado a Cisco IOS, NX-OS, Junos y RouterOS.

### 4. 🛡️ Trazabilidad Forense y Exportación de Auditoría (Módulo 5)
- **Inmutabilidad Criptográfica:** Cada acción de diagnóstico, remediación o despliegue genera un registro con hash SHA-256 en `audit.jsonl`.
- **Filtros Dinámicos:** Segmentación en caliente por dispositivo y estado operativo (`ALL`, `SUCCESS`, `FAILED`, `ROLLBACK`, `BLOCKED`).
- **Exportar JSON:** Exportación de registros para auditorías corporativas o integración SIEM.
- **Purgar Tests:** Depuración segura de eventos de prueba y ejecuciones sintéticas con confirmación de seguridad.

### 5. 🎯 Ergonomía y Navegación Contextual
- **Atajos Visibles en Botones:** Todos los botones interactivos incluyen su tecla asignada entre paréntesis: `Volver al Inicio (h)`, `+ Registrar Equipo (d)`, `Recargar (r)`, `Cancelar (Esc)`, `Cerrar (Esc)`, `Autorizar y Aplicar (Y)`, `Rechazar y Abortar (N)`.
- **Pie de Página Contextual:** Dentro de los 5 módulos operacionales, el único atajo visible es `h Inicio`, reduciendo distracciones y evitando activaciones accidentales.

---

## 📊 Métricas de Calidad y Cobertura

- **Total de Pruebas Automatizadas:** **172 pruebas** (`pytest tests/`) con 100% de aprobación en Linux, macOS y Windows.
- **Linter y Formato:** 0 errores y 0 advertencias con `ruff check .`
- **Sistemas Operativos de Red Certificados:**
  - Cisco IOS / IOS-XE
  - Cisco NX-OS (sesiones atómicas y checkpoints nativos)
  - Cisco IOS-XR (commit confirmed 180s)
  - Juniper Junos OS (commit confirmed 3m)
  - MikroTik RouterOS v6/v7 (backup binario)
- **Motores de Inferencia IA Soportados:**
  - Ollama (Inferencia local soberana y privada)
  - Google Gemini (`gemini-2.5-pro`, `gemini-2.5-flash`)
  - OpenAI (`gpt-4o`)
  - Anthropic Claude (`claude-3-5-sonnet`)

---

## ⚡ Instaladores y Métodos de Instalación

### 📥 1. Instalador Automatizado One-Click (Recomendado)
- **Windows (PowerShell):**
  ```powershell
  irm https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.ps1 | iex
  ```
- **Linux / macOS (POSIX Bash):**
  ```bash
  curl -sSL https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.sh | bash
  ```

### 📦 2. Binarios Autónomos Precompilados (Assets del Release)
No requieren Python ni dependencias previas:
- `networking-agent-v2.1.0-windows-x64.zip` (Ejecutable `.exe` portátil)
- `networking-agent-v2.1.0-linux-x64.tar.gz` (Binario Linux x64)

### 🛠️ 3. Instalación Manual para Desarrolladores
```bash
git clone https://github.com/GuifMur98/networkingAgent.git
cd networkingAgent
git checkout v2.1.0
uv sync --extra dev
uv run python main.py
```
