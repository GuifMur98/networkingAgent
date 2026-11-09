"""Native OS file dialog integration for PCAP import and export."""

from pathlib import Path
from typing import Optional


def _create_tk_root():
    """Create and configure a hidden Tk root window for dialogs."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    return root


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
        from tkinter import filedialog

        root = _create_tk_root()
        try:
            selected = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
                initialdir=default_dir or str(Path.cwd()),
            )
            return Path(selected) if selected else None
        finally:
            if root is not None and hasattr(root, "destroy"):
                try:
                    root.destroy()
                except Exception:
                    pass
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
        from tkinter import filedialog

        root = _create_tk_root()
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
            if root is not None and hasattr(root, "destroy"):
                try:
                    root.destroy()
                except Exception:
                    pass
    except Exception:
        return None
