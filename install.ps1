<#
.SYNOPSIS
    Automated Enterprise Installer for NetworkingAgent Enterprise (Windows x64)

.DESCRIPTION
    Sets up NetworkingAgent Enterprise in a self-contained local environment,
    registers the 'networking-agent' CLI/TUI command in the User PATH,
    and creates Desktop and Start Menu shortcuts.
    Supports both compiled standalone binary (.exe) and Python source setup.

.PARAMETER InstallDir
    Destination folder (default: $env:LOCALAPPDATA\NetworkingAgent).

.PARAMETER SkipShortcut
    Skip creating shortcuts.

.EXAMPLE
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.ps1" -OutFile "$env:TEMP\install.ps1"; & "$env:TEMP\install.ps1" 
#>

[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\NetworkingAgent",
    [switch]$SkipShortcut
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Text)
    Write-Host "[*] $Text" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[+] $Text" -ForegroundColor Green
}

function Write-WarningMsg {
    param([string]$Text)
    Write-Host "[!] $Text" -ForegroundColor Yellow
}

function Write-Banner {
    Write-Host ""
    Write-Host " =================================================================" -ForegroundColor Cyan
    Write-Host "    NetworkingAgent Enterprise v2.2.0 - Automated Windows Setup   " -ForegroundColor Yellow
    Write-Host "    Autonomous & Closed-Loop Network Assistant (Textual TUI)      " -ForegroundColor White
    Write-Host " =================================================================" -ForegroundColor Cyan
    Write-Host ""
}

Write-Banner

function Register-WindowsApp {
    param(
        [string]$InstallDir,
        [string]$AppIconPath,
        [string]$UninstallerPath
    )
    try {
        $RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NetworkingAgent"
        if (-not (Test-Path $RegPath)) {
            New-Item -Path $RegPath -Force | Out-Null
        }
        
        $EstimatedSizeKB = 0
        if (Test-Path $InstallDir) {
            $EstimatedSizeKB = [int]((Get-ChildItem -Path $InstallDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1KB)
        }
        
        Set-ItemProperty -Path $RegPath -Name "DisplayName" -Value "NetworkingAgent Enterprise"
        Set-ItemProperty -Path $RegPath -Name "DisplayVersion" -Value "2.2.0"
        Set-ItemProperty -Path $RegPath -Name "Publisher" -Value "NetworkingAgent Enterprise Team"
        Set-ItemProperty -Path $RegPath -Name "InstallLocation" -Value "$InstallDir"
        if (Test-Path $AppIconPath) {
            Set-ItemProperty -Path $RegPath -Name "DisplayIcon" -Value "$AppIconPath,0"
        }
        Set-ItemProperty -Path $RegPath -Name "UninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -File `"$UninstallerPath`""
        Set-ItemProperty -Path $RegPath -Name "QuietUninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -NonInteractive -File `"$UninstallerPath`""
        Set-ItemProperty -Path $RegPath -Name "InstallDate" -Value (Get-Date -Format "yyyyMMdd")
        Set-ItemProperty -Path $RegPath -Name "EstimatedSize" -Value $EstimatedSizeKB -Type DWord
        Set-ItemProperty -Path $RegPath -Name "HelpLink" -Value "https://github.com/GuifMur98/networkingAgent"
        Set-ItemProperty -Path $RegPath -Name "URLInfoAbout" -Value "https://github.com/GuifMur98/networkingAgent"
        Set-ItemProperty -Path $RegPath -Name "NoModify" -Value 1 -Type DWord
        Set-ItemProperty -Path $RegPath -Name "NoRepair" -Value 1 -Type DWord
        Write-Success "Registrado en Aplicaciones Instaladas de Windows (Panel de Control y Configuracion)."
    } catch {
        Write-WarningMsg "No se pudo registrar en la lista de programas de Windows: $_"
    }
}

# 1. Check if running alongside a compiled standalone binary (.exe)
$StandaloneExe = $null
if ($PSScriptRoot) {
    $Candidate = Join-Path $PSScriptRoot "networking-agent.exe"
    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        $StandaloneExe = $Candidate
    }
}

if ($StandaloneExe) {
    Write-Step "Paquete Standalone detectado: Instalando binario compilado..."
    Write-Step "Preparando directorio de instalación: $InstallDir"
    $BinDir = Join-Path $InstallDir "bin"
    if (-not (Test-Path $BinDir)) {
        New-Item -Path $BinDir -ItemType Directory -Force | Out-Null
    }
    
    $DestExe = Join-Path $BinDir "networking-agent.exe"
    Write-Step "Instalando ejecutable en $DestExe..."
    Get-Process -Name "networking-agent" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    Copy-Item -Path $StandaloneExe -Destination $DestExe -Force

    # Copy docs and assets if present
    foreach ($doc in @("README.md", "LICENSE")) {
        $docSrc = Join-Path $PSScriptRoot $doc
        if (Test-Path $docSrc) {
            Copy-Item -Path $docSrc -Destination (Join-Path $InstallDir $doc) -Force
        }
    }
    $AssetsSrc = Join-Path $PSScriptRoot "assets"
    $AssetsDst = Join-Path $InstallDir "assets"
    if (Test-Path $AssetsSrc) {
        if (-not (Test-Path $AssetsDst)) {
            New-Item -Path $AssetsDst -ItemType Directory -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $AssetsSrc "*") -Destination $AssetsDst -Recurse -Force
    }
    $AppIconPath = Join-Path $AssetsDst "app_icon.ico"
    if (-not (Test-Path $AppIconPath)) {
        $AppIconPath = $DestExe
    }

    # Add Bin to User PATH
    $UserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$BinDir*") {
        Write-Step "Agregando $BinDir a la variable de entorno PATH de usuario..."
        [System.Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
        $env:Path = "$env:Path;$BinDir"
        Write-Success "Agregado al PATH del usuario permanentemente."
    } else {
        Write-Success "$BinDir ya está registrado en el PATH."
    }

    # Create Shortcuts (Desktop + Start Menu)
    if (-not $SkipShortcut) {
        try {
            $WshShell = New-Object -ComObject WScript.Shell
            
            # Desktop Shortcut
            $DesktopPath = [System.Environment]::GetFolderPath("Desktop")
            $ShortcutPath = Join-Path $DesktopPath "NetworkingAgent NOC Console.lnk"
            $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
            $Shortcut.TargetPath = $DestExe
            $Shortcut.WorkingDirectory = $InstallDir
            $Shortcut.Description = "NetworkingAgent Enterprise NOC Mission Control Console"
            if (Test-Path $AppIconPath) {
                $Shortcut.IconLocation = "$AppIconPath,0"
            }
            $Shortcut.Save()
            Write-Success "Acceso directo en el Escritorio creado: $ShortcutPath"

            # Start Menu Shortcut
            $StartMenuPrograms = [System.Environment]::GetFolderPath("Programs")
            if (Test-Path $StartMenuPrograms) {
                $SmShortcutPath = Join-Path $StartMenuPrograms "NetworkingAgent.lnk"
                $SmShortcut = $WshShell.CreateShortcut($SmShortcutPath)
                $SmShortcut.TargetPath = $DestExe
                $SmShortcut.WorkingDirectory = $InstallDir
                $SmShortcut.Description = "NetworkingAgent Enterprise NOC Mission Control Console"
                if (Test-Path $AppIconPath) {
                    $SmShortcut.IconLocation = "$AppIconPath,0"
                }
                $SmShortcut.Save()
                Write-Success "Acceso directo en Menú Inicio creado: $SmShortcutPath"
            }
        } catch {
            Write-WarningMsg "No se pudieron crear algunos accesos directos: $_"
        }
    }

    # Create Uninstaller Script
    $UninstallerPath = Join-Path $InstallDir "uninstall.ps1"
    $UninstallerContent = @"
Write-Host '[*] Desinstalando NetworkingAgent Enterprise...' -ForegroundColor Cyan
`$InstallDir = '$InstallDir'
`$BinDir = '$BinDir'
`$DesktopShortcut = Join-Path ([System.Environment]::GetFolderPath('Desktop')) 'NetworkingAgent NOC Console.lnk'
`$SmShortcut = Join-Path ([System.Environment]::GetFolderPath('Programs')) 'NetworkingAgent.lnk'

if (Test-Path `$DesktopShortcut) { Remove-Item `$DesktopShortcut -Force }
if (Test-Path `$SmShortcut) { Remove-Item `$SmShortcut -Force }
`$RegPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NetworkingAgent'
if (Test-Path `$RegPath) { Remove-Item `$RegPath -Recurse -Force -ErrorAction SilentlyContinue }
`$UserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
`$NewPath = (`$UserPath -split ';' | Where-Object { `$_ -ne `$BinDir }) -join ';'
[System.Environment]::SetEnvironmentVariable('Path', `$NewPath, 'User')

Set-Location `$env:USERPROFILE
Remove-Item `$InstallDir -Recurse -Force
Write-Host '[+] NetworkingAgent desinstalado completamente.' -ForegroundColor Green
"@
    Set-Content -Path $UninstallerPath -Value $UninstallerContent -Encoding UTF8
    Register-WindowsApp -InstallDir $InstallDir -AppIconPath $AppIconPath -UninstallerPath $UninstallerPath

    Write-Host ""
    Write-Host " =================================================================" -ForegroundColor Green
    Write-Host " [EXITO] NetworkingAgent Enterprise v2.2.0 instalado con éxito!    " -ForegroundColor Green
    Write-Host " =================================================================" -ForegroundColor Green
    Write-Host " Para iniciar el agente, abre una nueva terminal y simplemente escribe:" -ForegroundColor White
    Write-Host "    networking-agent" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " O ejecútalo desde el acceso directo en tu Escritorio o Menú Inicio." -ForegroundColor White
    Write-Host " Desinstalador disponible en: $UninstallerPath" -ForegroundColor DarkGray
    Write-Host ""
    return
}

# 2. Source-based Setup (Repo or web stream via iex)
$IsLocalRepo = $false
$ScriptDir = $null

try {
    if ($PSScriptRoot -and (Test-Path -LiteralPath $PSScriptRoot -PathType Container)) {
        $CheckToml = Join-Path $PSScriptRoot "pyproject.toml"
        if (Test-Path -LiteralPath $CheckToml -PathType Leaf) {
            $IsLocalRepo = $true
            $ScriptDir = $PSScriptRoot
        }
    } elseif ($MyInvocation.MyCommand.Path -and (Test-Path -LiteralPath $MyInvocation.MyCommand.Path -PathType Leaf)) {
        $Parent = Split-Path -Parent $MyInvocation.MyCommand.Path
        $CheckToml = Join-Path $Parent "pyproject.toml"
        if (Test-Path -LiteralPath $CheckToml -PathType Leaf) {
            $IsLocalRepo = $true
            $ScriptDir = $Parent
        }
    }
} catch {
    $IsLocalRepo = $false
}

# 3. Check for uv or Python
Write-Step "Checking prerequisites (Python >= 3.12 or uv)..."
$UvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
$PythonCmd = Get-Command "python" -ErrorAction SilentlyContinue

if (-not $UvCmd -and -not $PythonCmd) {
    Write-Step "uv / Python not found. Downloading uv installer securely..."
    try {
        $TempInstaller = Join-Path ([System.IO.Path]::GetTempPath()) "uv-install-$([System.Guid]::NewGuid().ToString('N')).ps1"
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $TempInstaller -UseBasicParsing
        if ((Test-Path $TempInstaller) -and ((Get-Item $TempInstaller).Length -gt 1000)) {
            Write-Step "Executing verified local uv installer..."
            & powershell.exe -ExecutionPolicy Bypass -File $TempInstaller
            Remove-Item -Path $TempInstaller -Force -ErrorAction SilentlyContinue
        } else {
            throw "Downloaded installer was empty or invalid."
        }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $UvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
    } catch {
        Write-WarningMsg "Could not install uv automatically. Please install Python 3.12+ or uv manually."
    }
}

# 4. Create Installation Directory
Write-Step "Preparing installation directory: $InstallDir"
if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

$BinDir = Join-Path $InstallDir "bin"
if (-not (Test-Path $BinDir)) {
    New-Item -Path $BinDir -ItemType Directory -Force | Out-Null
}

# 5. Copy or Clone Repository
$AppSourceDir = Join-Path $InstallDir "app"
if ($IsLocalRepo) {
    Write-Step "Copying local repository files to $AppSourceDir..."
    if (Test-Path $AppSourceDir) {
        Remove-Item -Path $AppSourceDir -Recurse -Force | Out-Null
    }
    Copy-Item -Path $ScriptDir -Destination $AppSourceDir -Recurse -Exclude ".venv", "__pycache__", "build", "dist"
} else {
    Write-Step "Fetching NetworkingAgent repository from GitHub..."
    if (Test-Path $AppSourceDir) {
        Remove-Item -Path $AppSourceDir -Recurse -Force | Out-Null
    }
    
    $GitCmd = Get-Command "git" -ErrorAction SilentlyContinue
    if ($GitCmd) {
        & git clone --depth 1 https://github.com/GuifMur98/networkingAgent.git $AppSourceDir
    } else {
        Write-Step "Git not detected. Downloading source archive from GitHub..."
        $ZipPath = Join-Path $InstallDir "repo.zip"
        Invoke-RestMethod -Uri "https://github.com/GuifMur98/networkingAgent/archive/refs/heads/main.zip" -OutFile $ZipPath
        Expand-Archive -Path $ZipPath -DestinationPath $InstallDir -Force
        Remove-Item $ZipPath -Force
        $Extracted = Join-Path $InstallDir "networkingAgent-main"
        if (Test-Path $Extracted) {
            Move-Item -Path $Extracted -Destination $AppSourceDir -Force
        }
    }
}

# 6. Create Virtual Environment and Install Dependencies
Set-Location $AppSourceDir
$env:UV_LINK_MODE = "copy"

if ($UvCmd) {
    Write-Step "Setting up virtual environment with uv..."
    & uv venv (Join-Path $InstallDir "venv")
    $VenvPython = Join-Path (Join-Path $InstallDir "venv") "Scripts\python.exe"
    & uv pip install --python $VenvPython -e .
} elseif ($PythonCmd) {
    Write-Step "Setting up virtual environment with python venv..."
    & python -m venv (Join-Path $InstallDir "venv")
    $VenvPython = Join-Path (Join-Path $InstallDir "venv") "Scripts\python.exe"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -e .
} else {
    throw "Neither uv nor Python was available to create the virtual environment."
}

# 7. Generate Launcher Command (.cmd)
$LauncherPath = Join-Path $BinDir "networking-agent.cmd"
$LauncherContent = @"
@echo off
setlocal
set "NETWORKING_AGENT_HOME=$InstallDir"
set "NETWORKING_AGENT_DATA_DIR=$InstallDir\data"
cd /d "$AppSourceDir"
"$VenvPython" "$AppSourceDir\main.py" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] NetworkingAgent se cerro con codigo de salida %ERRORLEVEL%.
    pause
)
endlocal
"@
Set-Content -Path $LauncherPath -Value $LauncherContent -Encoding Ascii
Write-Success "Generated launcher script: $LauncherPath"

# 8. Add Bin to User PATH
$UserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    Write-Step "Adding $BinDir to User PATH environment variable..."
    [System.Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Success "Added to User PATH."
} else {
    Write-Success "$BinDir is already registered in User PATH."
}

# 9. Create Desktop & Start Menu Shortcuts with Official App Icon
if (-not $SkipShortcut) {
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        
        $AppIconPath = Join-Path $InstallDir "assets\app_icon.ico"
        if (-not (Test-Path $AppIconPath)) {
            $AppIconPath = Join-Path $AppSourceDir "assets\app_icon.ico"
        }

        # Desktop Shortcut
        $DesktopPath = [System.Environment]::GetFolderPath("Desktop")
        $ShortcutPath = Join-Path $DesktopPath "NetworkingAgent NOC Console.lnk"
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        
        $WtCmd = Get-Command "wt.exe" -ErrorAction SilentlyContinue
        if ($WtCmd) {
            $Shortcut.TargetPath = "wt.exe"
            $Shortcut.Arguments = "-p `"Command Prompt`" -d `"$AppSourceDir`" `"$LauncherPath`""
        } else {
            $Shortcut.TargetPath = "$LauncherPath"
            $Shortcut.Arguments = ""
        }
        $Shortcut.WorkingDirectory = $AppSourceDir
        $Shortcut.Description = "NetworkingAgent Enterprise NOC Mission Control Console"
        if (Test-Path $AppIconPath) {
            $Shortcut.IconLocation = "$AppIconPath,0"
        }
        $Shortcut.Save()
        Write-Success "Desktop shortcut created with icon: $ShortcutPath"

        # Start Menu Shortcut
        $StartMenuPrograms = [System.Environment]::GetFolderPath("Programs")
        if (Test-Path $StartMenuPrograms) {
            $SmShortcutPath = Join-Path $StartMenuPrograms "NetworkingAgent.lnk"
            $SmShortcut = $WshShell.CreateShortcut($SmShortcutPath)
            if ($WtCmd) {
                $SmShortcut.TargetPath = "wt.exe"
                $SmShortcut.Arguments = "-p `"Command Prompt`" -d `"$AppSourceDir`" `"$LauncherPath`""
            } else {
                $SmShortcut.TargetPath = "$LauncherPath"
                $SmShortcut.Arguments = ""
            }
            $SmShortcut.WorkingDirectory = $AppSourceDir
            $SmShortcut.Description = "NetworkingAgent Enterprise NOC Mission Control Console"
            if (Test-Path $AppIconPath) {
                $SmShortcut.IconLocation = "$AppIconPath,0"
            }
            $SmShortcut.Save()
            Write-Success "Start Menu shortcut created with icon: $SmShortcutPath"
        }
    } catch {
        Write-WarningMsg "Could not create Desktop shortcut: $_"
    }
}

# 10. Create Uninstaller Script
$UninstallerPath = Join-Path $InstallDir "uninstall.ps1"
$UninstallerContent = @"
Write-Host '[*] Uninstalling NetworkingAgent Enterprise...' -ForegroundColor Cyan
`$InstallDir = '$InstallDir'
`$BinDir = '$BinDir'
`$DesktopShortcut = Join-Path ([System.Environment]::GetFolderPath('Desktop')) 'NetworkingAgent NOC Console.lnk'
`$SmShortcut = Join-Path ([System.Environment]::GetFolderPath('Programs')) 'NetworkingAgent.lnk'

if (Test-Path `$DesktopShortcut) { Remove-Item `$DesktopShortcut -Force }
if (Test-Path `$SmShortcut) { Remove-Item `$SmShortcut -Force }
`$RegPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NetworkingAgent'
if (Test-Path `$RegPath) { Remove-Item `$RegPath -Recurse -Force -ErrorAction SilentlyContinue }
`$UserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
`$NewPath = (`$UserPath -split ';' | Where-Object { `$_ -ne `$BinDir }) -join ';'
[System.Environment]::SetEnvironmentVariable('Path', `$NewPath, 'User')

Set-Location `$env:USERPROFILE
Remove-Item `$InstallDir -Recurse -Force
Write-Host '[+] NetworkingAgent successfully removed.' -ForegroundColor Green
"@
Set-Content -Path $UninstallerPath -Value $UninstallerContent -Encoding UTF8
Register-WindowsApp -InstallDir $InstallDir -AppIconPath $AppIconPath -UninstallerPath $UninstallerPath

Write-Host ""
Write-Host " =================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] NetworkingAgent Enterprise v2.2.0 installed!           " -ForegroundColor Green
Write-Host " =================================================================" -ForegroundColor Green
Write-Host " To start the agent, open a new terminal and simply type:" -ForegroundColor White
Write-Host "    networking-agent" -ForegroundColor Yellow
Write-Host ""
Write-Host " Or launch it directly from the Desktop or Start Menu shortcut." -ForegroundColor White
Write-Host " Uninstaller located at: $UninstallerPath" -ForegroundColor DarkGray
Write-Host ""
