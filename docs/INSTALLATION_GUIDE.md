# Guía Definitiva de Instalación y Despliegue — NetworkingAgent Enterprise v2.1.1

Esta guía describe todas las alternativas de instalación y despliegue de **NetworkingAgent Enterprise v2.1.1**, desde instaladores automáticos de un solo clic hasta paquetes ejecutables portables (sin necesidad de instalar Python) y entornos de desarrollo.

---

## 📋 Resumen de Métodos de Instalación

| Método | Dirigido a | Requiere Python | Agrega a PATH | Accesos Directos |
| :--- | :--- | :---: | :---: | :---: |
| **A. Paquete de GitHub (`.zip`) con `instalar.bat`** | Usuarios finales en Windows | **No** | **Sí** (Automático) | Escritorio y Menú Inicio |
| **B. Comando Web Remoto (`irm` / `curl`)** | Instalación desatendida / Servidores | Automático | **Sí** (Automático) | Escritorio y Menú Inicio |
| **C. Portable Standalone (`iniciar.bat`)** | Ejecución desde USB / Sin instalar | **No** | No (Local) | No |
| **D. Repositorio de Desarrollo (`uv` / `git`)** | Desarrolladores y DevOps | Sí (>= 3.12) | Opcional | No |

---

## Opción 1: Paquete Precompilado de GitHub Releases (Recomendado para Windows)

No requiere tener instalado Python, Git ni compiladores en tu computadora.

### Paso 1: Descargar el Paquete
1. Ve a la sección de [Releases de GitHub](https://github.com/GuifMur98/networkingAgent/releases/tag/v2.1.1).
2. Descarga el archivo: **`networking-agent-v2.1.1-windows-x64.zip`**.
3. Haz clic derecho sobre el archivo `.zip` y selecciona **Extraer todo...** en la carpeta de tu preferencia.

### Paso 2: Instalación con 1 Clic (`instalar.bat`)
Dentro de la carpeta descomprimida encontrarás:
- **`instalar.bat`**: Haz **doble clic** sobre este archivo.

El instalador automatizado realizará las siguientes acciones en menos de 2 segundos:
1. Copiará el binario independiente a: `%LOCALAPPDATA%\NetworkingAgent\bin\networking-agent.exe`.
2. **Registrará permanentemente** la carpeta en la variable de entorno `PATH` de tu usuario.
3. Creará el acceso directo en tu **Escritorio**: `NetworkingAgent NOC Console`.
4. Creará el acceso directo en tu **Menú Inicio**: Permite buscar "NetworkingAgent" con la tecla Windows.
5. Generará el script de desinstalación limpia `uninstall.ps1`.

### Paso 3: ¿Cómo ejecutarlo?
Tras la instalación, puedes abrir NetworkingAgent de 3 formas distintas:
- **Opción Terminal:** Abre una nueva ventana de PowerShell, CMD o Windows Terminal y escribe:
  ```powershell
  networking-agent
  ```
- **Opción Escritorio:** Haz doble clic en el acceso directo `NetworkingAgent NOC Console`.
- **Opción Menú Inicio:** Presiona la tecla `Windows`, escribe `NetworkingAgent` y pulsa `Enter`.

---

## Opción 2: Instalación Automática por Comando Web (One-Click Terminal)

Si prefieres instalar directamente desde tu terminal sin descargar archivos manualmente en el navegador:

### En Windows (PowerShell):
Abre PowerShell y ejecuta:
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.ps1 -OutFile "$env:TEMP\install.ps1"
& "$env:TEMP\install.ps1"
```

> [!NOTE]
> Este método descarga primero el script a una ubicación temporal aislada y luego lo ejecuta (patrón en dos pasos seguro contra ejecución ciega en tuberías de shell), aprovisionando un entorno virtual Python aislado con `uv` en `%LOCALAPPDATA%\NetworkingAgent`, registrando el comando en el `PATH` y generando los accesos directos en el Escritorio y Menú Inicio.

### En Linux y macOS (Bash):
Abre tu terminal y ejecuta:
```bash
curl -fsSL https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
```

> [!NOTE]
> En entornos POSIX, el agente se instala en `~/.local/share/networking-agent` y el binario en `~/.local/bin/networking-agent`, agregándose automáticamente a tu `~/.bashrc` o `~/.zshrc`.

---

## Opción 3: Modo Portable (Sin Instalación en el Sistema)

Si deseas utilizar NetworkingAgent desde una memoria USB o probarlo sin registrar comandos en el sistema:

1. Descomprime `networking-agent-v2.1.1-windows-x64.zip`.
2. Haz doble clic en **`iniciar.bat`** (o en `networking-agent.exe`).
3. El agente se ejecutará de inmediato en modo interactivo.

---

## Opción 4: Instalación para Desarrolladores (Desde Código Fuente)

Para desarrolladores que deseen modificar el código, ejecutar pruebas o crear nuevos drivers:

### Prerrequisitos
- Python `>= 3.12` (compatible y probado hasta Python `3.14`).
- Administrador de paquetes [`uv`](https://github.com/astral-sh/uv).
- Git.

### Pasos de Instalación:
```powershell
# 1. Clonar el repositorio
git clone https://github.com/GuifMur98/networkingAgent.git
cd networkingAgent

# 2. Sincronizar el entorno virtual y dependencias con uv
uv sync --extra dev

# 3. Ejecutar la consola TUI reactiva
uv run networking-agent

# O iniciar directamente con Python:
uv run python main.py
```

### Ejecutar la Suite de Pruebas Automatizadas:
```powershell
uv run pytest
```
*Debe reportar 189 pruebas aprobadas (100% passing).*

---

## 🔍 Verificación Post-Instalación

Para confirmar que el agente quedó correctamente registrado en tu sistema operativo:

1. **Verificar que el comando está reconocido en el PATH:**
   ```powershell
   Get-Command networking-agent
   ```
   *Debe responder con la ruta al ejecutable o lanzador.*

2. **Verificar la versión del software:**
   ```powershell
   networking-agent --version
   ```
   *Salida esperada:* `networking-agent 2.1.1`

3. **Verificar el menú de ayuda y opciones CLI:**
   ```powershell
   networking-agent --help
   ```

4. **Verificar el arranque de la Interfaz TUI:**
   Ejecuta:
   ```powershell
   networking-agent
   ```
   Se desplegará la consola **Cyberpunk Mission Control** con las 6 pestañas operacionales (*Inicio*, *Diagnóstico*, *Configuración*, *Inventario*, *Automatización*, *Auditoría*) y el atajo de la Paleta de Comandos (`[P] Paleta de Comandos` / `Ctrl+P`) en la esquina inferior derecha.

---

## 🧹 Desinstalación Limpia

Si en algún momento deseas desinstalar NetworkingAgent Enterprise:

### En Windows:
Ejecuta en PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\NetworkingAgent\uninstall.ps1"
```
*Esto eliminará el directorio de la aplicación, retirará la ruta del `PATH` del usuario y borrará los accesos directos del Escritorio y Menú Inicio.*

### En Linux / macOS:
```bash
~/.local/share/networking-agent/uninstall.sh
```

---

## ❓ Preguntas Frecuentes y Resolución de Problemas

### 1. Escribo `networking-agent` pero PowerShell dice que no se reconoce el comando
**Causa:** La ventana de terminal estaba abierta antes de que el instalador modificara la variable `PATH`.
**Solución:** Cierra esa ventana de terminal y abre una **nueva ventana** de PowerShell para que cargue las variables de entorno actualizadas.

### 2. Windows Defender o SmartScreen muestra una advertencia ("Windows protegió su PC")
**Causa:** Como el binario ejecutable fue compilado recientemente por ti o en GitHub Actions sin un certificado comercial EV firmado de pago, Windows SmartScreen previene la ejecución por precaución.
**Solución:** Haz clic en **Más información** y luego en **Ejecutar de todas formas**.

### 3. Error de política de ejecución de PowerShell (`about_Execution_Policies`)
**Causa:** Tu sistema tiene deshabilitada la ejecución de scripts `.ps1` por defecto.
**Solución:** Utiliza el instalador `instalar.bat` (que ejecuta el script con el bypass de seguridad correspondiente) o abre PowerShell como administrador y ejecuta:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 4. ¿Dónde se guardan mis equipos y claves cifradas?
Toda la información se almacena localmente en tu equipo:
- Base de datos SQLite cifrada (modo WAL): `%LOCALAPPDATA%\NetworkingAgent\data\networking_agent.db`
- Clave criptográfica simétrica (AES-128-CBC Fernet): Variable de entorno `NETWORKING_AGENT_VAULT_KEY` o `%USERPROFILE%\.networking_agent_vault.key`.
- Bitácora inmutable de auditoría: `%LOCALAPPDATA%\NetworkingAgent\logs\audit.jsonl`.
