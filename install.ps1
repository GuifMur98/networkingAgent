<#
.SYNOPSIS
    Automated Enterprise Installer for NetworkingAgent Enterprise (Windows x64)

.DESCRIPTION
    Sets up NetworkingAgent Enterprise in a self-contained local environment,
    installs runtime dependencies via uv/pip, registers the 'networking-agent'
    CLI/TUI command in the User PATH, and creates a Desktop shortcut.

.PARAMETER InstallDir
    Destination folder (default: $env:LOCALAPPDATA\NetworkingAgent).

.PARAMETER SkipShortcut
    Skip creating a Desktop shortcut.

.EXAMPLE
    irm https://raw.githubusercontent.com/GuifMur98/networkingAgent/main/install.ps1 | iex
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
    Write-Host "    NetworkingAgent Enterprise v2.1.0 - Automated Windows Setup   " -ForegroundColor Yellow
    Write-Host "    Autonomous & Closed-Loop Network Assistant (Textual TUI)      " -ForegroundColor White
    Write-Host " =================================================================" -ForegroundColor Cyan
    Write-Host ""
}

Write-Banner

# 1. Determine Source Directory or Clone
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$IsLocalRepo = Test-Path (Join-Path $ScriptDir "pyproject.toml")

# 2. Check for uv or Python
Write-Step "Checking prerequisites (Python >= 3.12 or uv)..."
$UvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
$PythonCmd = Get-Command "python" -ErrorAction SilentlyContinue

if (-not $UvCmd -and -not $PythonCmd) {
    Write-Step "uv / Python not found. Installing uv package manager..."
    try {
        irm https://astral.sh/uv/install.ps1 | iex
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $UvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
    } catch {
        Write-WarningMsg "Could not install uv automatically. Please install Python 3.12+ or uv manually."
    }
}

# 3. Create Installation Directory
Write-Step "Preparing installation directory: $InstallDir"
if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

$BinDir = Join-Path $InstallDir "bin"
if (-not (Test-Path $BinDir)) {
    New-Item -Path $BinDir -ItemType Directory -Force | Out-Null
}

# 4. Copy or Clone Repository
$AppSourceDir = Join-Path $InstallDir "app"
if ($IsLocalRepo) {
    Write-Step "Copying local repository files to $AppSourceDir..."
    if (Test-Path $AppSourceDir) {
        Remove-Item -Path $AppSourceDir -Recurse -Force | Out-Null
    }
    Copy-Item -Path $ScriptDir -Destination $AppSourceDir -Recurse -Exclude ".venv", "__pycache__", "build", "dist"
} else {
    Write-Step "Cloning NetworkingAgent repository from GitHub..."
    if (Test-Path $AppSourceDir) {
        Remove-Item -Path $AppSourceDir -Recurse -Force | Out-Null
    }
    git clone --depth 1 https://github.com/GuifMur98/networkingAgent.git $AppSourceDir
}

# 5. Create Virtual Environment and Install Dependencies
Set-Location $AppSourceDir
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

# 6. Generate Launcher Command (.cmd)
$LauncherPath = Join-Path $BinDir "networking-agent.cmd"
$LauncherContent = @"
@echo off
setlocal
set "NETWORKING_AGENT_HOME=$InstallDir"
"$VenvPython" "$AppSourceDir\main.py" %*
endlocal
"@
Set-Content -Path $LauncherPath -Value $LauncherContent -Encoding Ascii
Write-Success "Generated launcher script: $LauncherPath"

# 7. Add Bin to User PATH
$UserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    Write-Step "Adding $BinDir to User PATH environment variable..."
    [System.Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Success "Added to User PATH."
} else {
    Write-Success "$BinDir is already registered in User PATH."
}

# 8. Create Desktop Shortcut (Optional)
if (-not $SkipShortcut) {
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $DesktopPath = [System.Environment]::GetFolderPath("Desktop")
        $ShortcutPath = Join-Path $DesktopPath "NetworkingAgent NOC Console.lnk"
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        
        # Check if Windows Terminal is installed
        $WtCmd = Get-Command "wt.exe" -ErrorAction SilentlyContinue
        if ($WtCmd) {
            $Shortcut.TargetPath = "wt.exe"
            $Shortcut.Arguments = "-p `"PowerShell`" -d `"$AppSourceDir`" `"$LauncherPath`""
        } else {
            $Shortcut.TargetPath = "powershell.exe"
            $Shortcut.Arguments = "-NoExit -Command `"& '$LauncherPath'`""
        }
        $Shortcut.WorkingDirectory = $AppSourceDir
        $Shortcut.Description = "NetworkingAgent Enterprise NOC Mission Control Console"
        $Shortcut.Save()
        Write-Success "Desktop shortcut created: $ShortcutPath"
    } catch {
        Write-WarningMsg "Could not create Desktop shortcut: $_"
    }
}

# 9. Create Uninstaller Script
$UninstallerPath = Join-Path $InstallDir "uninstall.ps1"
$UninstallerContent = @"
Write-Host '[*] Uninstalling NetworkingAgent Enterprise...' -ForegroundColor Cyan
`$InstallDir = '$InstallDir'
`$BinDir = '$BinDir'
`$DesktopShortcut = Join-Path ([System.Environment]::GetFolderPath('Desktop')) 'NetworkingAgent NOC Console.lnk'

if (Test-Path `$DesktopShortcut) { Remove-Item `$DesktopShortcut -Force }
`$UserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
`$NewPath = (`$UserPath -split ';' | Where-Object { `$_ -ne `$BinDir }) -join ';'
[System.Environment]::SetEnvironmentVariable('Path', `$NewPath, 'User')

Set-Location `$env:USERPROFILE
Remove-Item `$InstallDir -Recurse -Force
Write-Host '[+] NetworkingAgent successfully removed.' -ForegroundColor Green
"@
Set-Content -Path $UninstallerPath -Value $UninstallerContent -Encoding UTF8

Write-Host ""
Write-Host " =================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] NetworkingAgent Enterprise v2.1.0 installed!           " -ForegroundColor Green
Write-Host " =================================================================" -ForegroundColor Green
Write-Host " To start the agent, open a new terminal and simply type:" -ForegroundColor White
Write-Host "    networking-agent" -ForegroundColor Yellow
Write-Host ""
Write-Host " Or launch it directly from the Desktop shortcut." -ForegroundColor White
Write-Host " Uninstaller located at: $UninstallerPath" -ForegroundColor DarkGray
Write-Host ""
