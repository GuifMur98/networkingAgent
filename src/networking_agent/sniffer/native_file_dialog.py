"""Native OS file dialog integration for PCAP import and export."""

from pathlib import Path
from typing import Optional


def open_native_file_dialog(
    title: str = "Cargar archivo de captura PCAP",
    filetypes: Optional[list[tuple[str, str]]] = None,
    default_dir: Optional[str] = None,
) -> Optional[Path]:
    """Display native Windows/OS Open File Dialog and return selected Path, or None if cancelled."""
    if filetypes is None:
        filetypes = [
            ("Archivos de Captura (*.pcap, *.pcapng, *.cap)", "*.pcap;*.pcapng;*.cap"),
            ("Todos los archivos (*.*)", "*.*"),
        ]

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            selected = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
                initialdir=default_dir or str(Path.cwd()),
            )
            return Path(selected) if selected else None
        finally:
            root.destroy()
    except Exception:
        return None


def save_native_file_dialog(
    title: str = "Guardar captura en archivo PCAP",
    default_filename: str = "captura_red.pcap",
    filetypes: Optional[list[tuple[str, str]]] = None,
    default_dir: Optional[str] = None,
) -> Optional[Path]:
    """Display native Windows/OS Save File Dialog and return target Path, or None if cancelled."""
    if filetypes is None:
        filetypes = [
            ("Archivo PCAP (*.pcap)", "*.pcap"),
            ("Todos los archivos (*.*)", "*.*"),
        ]

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            selected = filedialog.asksaveasfilename(
                title=title,
                initialfile=default_filename,
                defaultextension=".pcap",
                filetypes=filetypes,
                initialdir=default_dir or str(Path.cwd()),
            )
            return Path(selected) if selected else None
        finally:
            root.destroy()
    except Exception:
        return None
