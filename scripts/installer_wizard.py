"""NetworkingAgent Enterprise - Native Windows Setup Wizard.

A professional, self-contained single-executable installer for Windows.
Embeds the pre-compiled application binary, assets, and documentation.
Provides both a sleek GUI wizard (Tkinter) and headless silent installation (/S).
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None

VERSION = "2.1.1"
APP_NAME = "NetworkingAgent Enterprise"
DEFAULT_INSTALL_DIR = os.path.expandvars(r"%LOCALAPPDATA%\NetworkingAgent")


def get_bundle_dir() -> Path:
    """Return bundle root directory (supports PyInstaller sys._MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def is_windows() -> bool:
    return sys.platform == "win32"


def refresh_windows_shell():
    """Notify Windows Shell that icons and associations have changed."""
    if not is_windows():
        return
    try:
        import ctypes

        # SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0)
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def add_to_user_path(bin_dir: Path) -> bool:
    """Add bin_dir to user PATH in registry if not already present."""
    if not is_windows() or not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""

        bin_dir_str = str(bin_dir)
        paths = [p for p in current_path.split(";") if p.strip()]
        if bin_dir_str not in paths:
            paths.append(bin_dir_str)
            new_path = ";".join(paths)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

            # Broadcast WM_SETTINGCHANGE so new shells inherit updated PATH
            import ctypes

            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_ulong()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result),
            )
            return True
        return False
    except Exception as e:
        print(f"[!] Warning: Could not update PATH: {e}")
        return False


def create_windows_shortcut(shortcut_path: Path, target_exe: Path, work_dir: Path, icon_path: Path, description: str):
    """Create a Windows .lnk shortcut using PowerShell COM object."""
    ps_cmd = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target_exe}'
$Shortcut.WorkingDirectory = '{work_dir}'
$Shortcut.Description = '{description}'
if (Test-Path '{icon_path}') {{
    $Shortcut.IconLocation = '{icon_path},0'
}}
$Shortcut.Save()
"""
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0,
    )


def register_in_windows_installed_apps(install_dir: Path, app_icon_path: Path, uninstaller_path: Path):
    """Register application in HKCU Uninstall registry for Settings & Control Panel."""
    if not is_windows() or not winreg:
        return
    try:
        reg_sub = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NetworkingAgent"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_sub)

        # Estimate size in KB
        size_kb = 0
        for root, _, files in os.walk(install_dir):
            for f in files:
                try:
                    size_kb += (Path(root) / f).stat().st_size // 1024
                except Exception:
                    pass

        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "NetworkingAgent Enterprise Team")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        if app_icon_path.exists():
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{app_icon_path},0")
        winreg.SetValueEx(
            key,
            "UninstallString",
            0,
            winreg.REG_SZ,
            f'powershell.exe -ExecutionPolicy Bypass -File "{uninstaller_path}"',
        )
        winreg.SetValueEx(
            key,
            "QuietUninstallString",
            0,
            winreg.REG_SZ,
            f'powershell.exe -ExecutionPolicy Bypass -NonInteractive -File "{uninstaller_path}"',
        )
        winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, today_str)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
        winreg.SetValueEx(key, "HelpLink", 0, winreg.REG_SZ, "https://github.com/GuifMur98/networkingAgent")
        winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "https://github.com/GuifMur98/networkingAgent")
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[!] Warning: Could not register in Windows Uninstall registry: {e}")


def write_uninstaller_script(install_dir: Path, bin_dir: Path) -> Path:
    """Generate clean PowerShell uninstaller in install directory."""
    uninstaller_path = install_dir / "uninstall.ps1"
    content = f"""# NetworkingAgent Enterprise Uninstaller
Write-Host '[*] Desinstalando NetworkingAgent Enterprise...' -ForegroundColor Cyan
$InstallDir = '{install_dir}'
$BinDir = '{bin_dir}'
$DesktopShortcut = Join-Path ([System.Environment]::GetFolderPath('Desktop')) 'NetworkingAgent NOC Console.lnk'
$SmShortcut = Join-Path ([System.Environment]::GetFolderPath('Programs')) 'NetworkingAgent.lnk'

if (Test-Path $DesktopShortcut) {{ Remove-Item $DesktopShortcut -Force -ErrorAction SilentlyContinue }}
if (Test-Path $SmShortcut) {{ Remove-Item $SmShortcut -Force -ErrorAction SilentlyContinue }}

$RegPath = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\NetworkingAgent'
if (Test-Path $RegPath) {{ Remove-Item $RegPath -Recurse -Force -ErrorAction SilentlyContinue }}

$UserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -like "*$BinDir*") {{
    $NewPath = ($UserPath -split ';' | Where-Object {{ $_ -ne $BinDir }}) -join ';'
    [System.Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
}}

Set-Location $env:USERPROFILE
Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host '[+] NetworkingAgent desinstalado completamente de su sistema.' -ForegroundColor Green
"""
    uninstaller_path.write_text(content, encoding="utf-8")
    return uninstaller_path


def perform_installation(
    install_dir: Path,
    create_desktop: bool = True,
    create_start_menu: bool = True,
    add_path: bool = True,
    progress_callback=None,
) -> bool:
    """Perform file extraction, shortcut setup, PATH configuration, and registry entry."""

    def update(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
        else:
            print(f"[{pct:3d}%] {msg}")

    update(5, "Preparando directorios del sistema...")
    bundle_dir = get_bundle_dir()
    bin_dir = install_dir / "bin"
    assets_dir = install_dir / "assets"

    bin_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Locate and copy application executable
    update(20, "Instalando binario ejecutable (networking-agent.exe)...")
    candidate_exes = [
        bundle_dir / "networking-agent.exe",
        bundle_dir / "bin" / "networking-agent.exe",
        bundle_dir / "dist" / "networking-agent.exe",
        Path("dist/networking-agent.exe"),
    ]
    app_exe_src = None
    for cand in candidate_exes:
        if cand.exists():
            app_exe_src = cand
            break

    dest_exe = bin_dir / "networking-agent.exe"
    if app_exe_src:
        shutil.copy2(app_exe_src, dest_exe)
    else:
        # Source fallback launcher if binary not bundled directly
        launcher_cmd = bin_dir / "networking-agent.cmd"
        launcher_cmd.write_text(f'@echo off\r\ncd /d "{install_dir}"\r\npython main.py %*\r\n', encoding="ascii")
        dest_exe = launcher_cmd

    # 2. Copy assets and icons
    update(45, "Copiando iconos oficiales e imágenes de marca...")
    bundle_assets = bundle_dir / "assets"
    if not bundle_assets.exists():
        bundle_assets = Path("assets")

    if bundle_assets.exists():
        for asset_file in bundle_assets.glob("*.*"):
            shutil.copy2(asset_file, assets_dir / asset_file.name)

    app_icon_path = assets_dir / "app_icon.ico"
    if not app_icon_path.exists():
        app_icon_path = dest_exe

    # 3. Copy documentation and licenses
    update(60, "Instalando documentación y licencias...")
    for doc in ["README.md", "LICENSE"]:
        doc_src = bundle_dir / doc
        if not doc_src.exists():
            doc_src = Path(doc)
        if doc_src.exists():
            shutil.copy2(doc_src, install_dir / doc)

    # 4. PATH integration
    if add_path:
        update(75, "Registrando comando en variable de entorno PATH...")
        add_to_user_path(bin_dir)

    # 5. Create uninstaller script
    uninstaller_path = write_uninstaller_script(install_dir, bin_dir)

    # 6. Windows Shortcuts
    update(85, "Creando accesos directos de escritorio y menú inicio...")
    if create_desktop and is_windows():
        desktop_path = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
        if not desktop_path.exists():
            desktop_path = Path(os.path.expandvars(r"%ONEDRIVE%\Desktop"))
        if desktop_path.exists():
            create_windows_shortcut(
                desktop_path / "NetworkingAgent NOC Console.lnk",
                dest_exe,
                install_dir,
                app_icon_path,
                "NetworkingAgent Enterprise NOC Mission Control Console",
            )

    if create_start_menu and is_windows():
        start_menu_programs = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
        if start_menu_programs.exists():
            create_windows_shortcut(
                start_menu_programs / "NetworkingAgent.lnk",
                dest_exe,
                install_dir,
                app_icon_path,
                "NetworkingAgent Enterprise NOC Mission Control Console",
            )

    # 7. Register in Windows Installed Apps
    update(95, "Registrando en Aplicaciones Instaladas de Windows...")
    register_in_windows_installed_apps(install_dir, app_icon_path, uninstaller_path)

    # 8. Refresh icon cache
    refresh_windows_shell()
    update(100, "¡Instalación completada exitosamente!")
    return True


def run_gui_wizard():
    """Launch the modern graphical Tkinter setup wizard."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from PIL import Image, ImageTk

    root = tk.Tk()
    root.title(f"Instalador de {APP_NAME} v{VERSION}")
    root.geometry("640x480")
    root.resizable(False, False)

    # Colors
    BG_DARK = "#0a0f1d"
    SURFACE_DARK = "#111827"
    TEXT_LIGHT = "#f8fafc"
    TEXT_DIM = "#94a3b8"
    CYAN_ACCENT = "#00e5ff"
    BORDER_COLOR = "#1e293b"

    root.configure(bg=BG_DARK)

    # Set window icon
    bundle_dir = get_bundle_dir()
    installer_ico = bundle_dir / "assets" / "installer_icon.ico"
    if not installer_ico.exists():
        installer_ico = Path("assets/installer_icon.ico")
    if installer_ico.exists() and is_windows():
        try:
            root.iconbitmap(str(installer_ico))
        except Exception:
            pass

    # State variables
    install_dir_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)
    create_desktop_var = tk.BooleanVar(value=True)
    create_start_menu_var = tk.BooleanVar(value=True)
    add_path_var = tk.BooleanVar(value=True)
    launch_app_var = tk.BooleanVar(value=True)

    # Style ttk widgets
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "TProgressbar",
        troughcolor=SURFACE_DARK,
        background=CYAN_ACCENT,
        bordercolor=BORDER_COLOR,
        thickness=18,
    )

    # Container frames
    page_welcome = tk.Frame(root, bg=BG_DARK)
    page_installing = tk.Frame(root, bg=BG_DARK)
    page_finished = tk.Frame(root, bg=BG_DARK)

    for p in (page_welcome, page_installing, page_finished):
        p.place(x=0, y=0, width=640, height=480)

    # ---------------- PAGE 1: WELCOME & OPTIONS ----------------
    # Header Banner Image
    logo_path = bundle_dir / "assets" / "installer_logo.png"
    if not logo_path.exists():
        logo_path = Path("assets/installer_logo.png")

    img_ref = None
    if logo_path.exists():
        try:
            pil_img = Image.open(logo_path)
            # scale preserving aspect ratio to width ~220
            w, h = pil_img.size
            scale = 220 / w
            pil_img = pil_img.resize((220, int(h * scale)), Image.Resampling.LANCZOS)
            img_ref = ImageTk.PhotoImage(pil_img)
            logo_label = tk.Label(page_welcome, image=img_ref, bg=BG_DARK)
            logo_label.image = img_ref
            logo_label.pack(pady=(18, 4))
        except Exception:
            pass

    title_lbl = tk.Label(
        page_welcome,
        text=f"{APP_NAME} v{VERSION}",
        font=("Segoe UI", 16, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_DARK,
    )
    title_lbl.pack()

    subtitle_lbl = tk.Label(
        page_welcome,
        text="Asistente Autónomo de Ingeniería de Redes en Bucle Cerrado con IA",
        font=("Segoe UI", 9),
        fg=CYAN_ACCENT,
        bg=BG_DARK,
    )
    subtitle_lbl.pack(pady=(0, 14))

    # Options Box
    options_frame = tk.LabelFrame(
        page_welcome,
        text=" Configuración de Instalación ",
        font=("Segoe UI", 9, "bold"),
        fg=TEXT_LIGHT,
        bg=SURFACE_DARK,
        bd=1,
        relief="solid",
    )
    options_frame.pack(padx=30, pady=5, fill="x")

    # Directory selector
    dir_label = tk.Label(
        options_frame,
        text="Carpeta de destino:",
        font=("Segoe UI", 9),
        fg=TEXT_LIGHT,
        bg=SURFACE_DARK,
    )
    dir_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

    dir_entry = tk.Entry(
        options_frame,
        textvariable=install_dir_var,
        font=("Segoe UI", 9),
        bg="#1e293b",
        fg=TEXT_LIGHT,
        insertbackground=TEXT_LIGHT,
        bd=1,
        relief="solid",
    )
    dir_entry.grid(row=1, column=0, padx=(12, 6), pady=(0, 10), sticky="ew")
    options_frame.grid_columnconfigure(0, weight=1)

    def browse_dir():
        d = filedialog.askdirectory(initialdir=install_dir_var.get())
        if d:
            install_dir_var.set(os.path.normpath(d))

    browse_btn = tk.Button(
        options_frame,
        text="Examinar...",
        command=browse_dir,
        font=("Segoe UI", 8, "bold"),
        bg="#334155",
        fg=TEXT_LIGHT,
        activebackground="#475569",
        activeforeground=TEXT_LIGHT,
        relief="flat",
        cursor="hand2",
    )
    browse_btn.grid(row=1, column=1, padx=(0, 12), pady=(0, 10))

    # Checkboxes
    cb_desktop = tk.Checkbutton(
        options_frame,
        text="Crear acceso directo en el Escritorio (con icono oficial de red)",
        variable=create_desktop_var,
        font=("Segoe UI", 9),
        fg=TEXT_LIGHT,
        bg=SURFACE_DARK,
        selectcolor=BG_DARK,
        activebackground=SURFACE_DARK,
        activeforeground=TEXT_LIGHT,
    )
    cb_desktop.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=2)

    cb_sm = tk.Checkbutton(
        options_frame,
        text="Crear acceso directo en el Menú Inicio de Windows",
        variable=create_start_menu_var,
        font=("Segoe UI", 9),
        fg=TEXT_LIGHT,
        bg=SURFACE_DARK,
        selectcolor=BG_DARK,
        activebackground=SURFACE_DARK,
        activeforeground=TEXT_LIGHT,
    )
    cb_sm.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=2)

    cb_path = tk.Checkbutton(
        options_frame,
        text="Agregar comando global 'networking-agent' al PATH del sistema",
        variable=add_path_var,
        font=("Segoe UI", 9),
        fg=TEXT_LIGHT,
        bg=SURFACE_DARK,
        selectcolor=BG_DARK,
        activebackground=SURFACE_DARK,
        activeforeground=TEXT_LIGHT,
    )
    cb_path.grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 10))

    # Bottom action buttons
    bottom_frame = tk.Frame(page_welcome, bg=BG_DARK)
    bottom_frame.pack(side="bottom", fill="x", padx=30, pady=20)

    def on_cancel():
        if messagebox.askyesno("Cancelar Instalación", "¿Deseas salir del asistente de instalación?"):
            root.destroy()

    cancel_btn = tk.Button(
        bottom_frame,
        text="Cancelar",
        command=on_cancel,
        font=("Segoe UI", 9),
        bg="#334155",
        fg=TEXT_LIGHT,
        activebackground="#475569",
        activeforeground=TEXT_LIGHT,
        relief="flat",
        padx=18,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="left")

    def start_install_flow():
        page_welcome.lower()
        page_installing.lift()
        root.update()

        def gui_progress(pct: int, msg: str):
            progress_bar["value"] = pct
            progress_lbl.config(text=msg)
            root.update()
            time.sleep(0.04)

        try:
            target = Path(install_dir_var.get())
            success = perform_installation(
                target,
                create_desktop=create_desktop_var.get(),
                create_start_menu=create_start_menu_var.get(),
                add_path=add_path_var.get(),
                progress_callback=gui_progress,
            )
            if success:
                page_installing.lower()
                page_finished.lift()
        except Exception as ex:
            messagebox.showerror("Error de Instalación", f"Ocurrió un error al instalar:\n\n{ex}")
            root.destroy()

    install_btn = tk.Button(
        bottom_frame,
        text="Instalar Ahora",
        command=start_install_flow,
        font=("Segoe UI", 9, "bold"),
        bg=CYAN_ACCENT,
        fg="#000000",
        activebackground="#38bdf8",
        activeforeground="#000000",
        relief="flat",
        padx=22,
        pady=4,
        cursor="hand2",
    )
    install_btn.pack(side="right")

    # ---------------- PAGE 2: PROGRESS SCREEN ----------------
    inst_title = tk.Label(
        page_installing,
        text="Instalando NetworkingAgent Enterprise...",
        font=("Segoe UI", 14, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_DARK,
    )
    inst_title.pack(pady=(120, 10))

    progress_lbl = tk.Label(
        page_installing,
        text="Iniciando...",
        font=("Segoe UI", 9),
        fg=TEXT_DIM,
        bg=BG_DARK,
    )
    progress_lbl.pack(pady=(0, 14))

    progress_bar = ttk.Progressbar(
        page_installing, style="TProgressbar", orient="horizontal", length=480, mode="determinate"
    )
    progress_bar.pack(pady=10)

    # ---------------- PAGE 3: FINISHED SCREEN ----------------
    fin_title = tk.Label(
        page_finished,
        text="¡Instalación Completada con Éxito!",
        font=("Segoe UI", 16, "bold"),
        fg="#4ade80",
        bg=BG_DARK,
    )
    fin_title.pack(pady=(110, 10))

    fin_desc = tk.Label(
        page_finished,
        text=f"{APP_NAME} ha sido instalado correctamente en su sistema.\n"
        "Se crearon los accesos directos con el icono oficial y se registró en Windows.",
        font=("Segoe UI", 10),
        fg=TEXT_LIGHT,
        bg=BG_DARK,
        justify="center",
    )
    fin_desc.pack(pady=(0, 20))

    cb_launch = tk.Checkbutton(
        page_finished,
        text="Iniciar NetworkingAgent Enterprise ahora",
        variable=launch_app_var,
        font=("Segoe UI", 10, "bold"),
        fg=CYAN_ACCENT,
        bg=BG_DARK,
        selectcolor="#111827",
        activebackground=BG_DARK,
        activeforeground=CYAN_ACCENT,
        cursor="hand2",
    )
    cb_launch.pack(pady=10)

    def on_finish():
        if launch_app_var.get():
            target = Path(install_dir_var.get())
            app_exe = target / "bin" / "networking-agent.exe"
            if not app_exe.exists():
                app_exe = target / "bin" / "networking-agent.cmd"
            if app_exe.exists():
                if str(app_exe).endswith(".exe"):
                    subprocess.Popen([str(app_exe)], cwd=str(target))
                else:
                    subprocess.Popen(["cmd.exe", "/c", str(app_exe)], cwd=str(target))
        root.destroy()

    finish_btn = tk.Button(
        page_finished,
        text="Finalizar",
        command=on_finish,
        font=("Segoe UI", 10, "bold"),
        bg=CYAN_ACCENT,
        fg="#000000",
        activebackground="#38bdf8",
        activeforeground="#000000",
        relief="flat",
        padx=28,
        pady=6,
        cursor="hand2",
    )
    finish_btn.pack(pady=20)

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{VERSION} Setup")
    parser.add_argument(
        "-s",
        "--silent",
        "/S",
        dest="silent",
        action="store_true",
        help="Ejecución desatendida silenciosa",
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="install_dir",
        default=DEFAULT_INSTALL_DIR,
        help="Directorio de destino",
    )
    parser.add_argument("--no-desktop", dest="no_desktop", action="store_true", help="No crear acceso en Escritorio")
    parser.add_argument(
        "--no-start-menu",
        dest="no_start_menu",
        action="store_true",
        help="No crear acceso en Menú Inicio",
    )
    parser.add_argument("--no-path", dest="no_path", action="store_true", help="No agregar a variable PATH")

    args, _ = parser.parse_known_args()

    if args.silent:
        target = Path(os.path.expandvars(args.install_dir))
        success = perform_installation(
            target,
            create_desktop=not args.no_desktop,
            create_start_menu=not args.no_start_menu,
            add_path=not args.no_path,
        )
        sys.exit(0 if success else 1)
    else:
        run_gui_wizard()


if __name__ == "__main__":
    main()
