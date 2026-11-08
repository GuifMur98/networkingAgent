"""Robust and validated interactive prompt helpers with continuous re-prompting on invalid input."""

from typing import List, Optional, Set

from rich.prompt import Prompt

from networking_agent.core.logging import console

AFFIRMATIVE_RESPONSES: Set[str] = {"s", "si", "sí", "y", "yes", "confirmar", "true"}
NEGATIVE_RESPONSES: Set[str] = {"n", "no", "cancelar", "rechazar", "abortar", "false"}


def prompt_hitl_approval() -> bool:
    """Prompts operator for Human-in-the-Loop authorization.

    Continuously re-prompts if the user enters anything different from the expected choices,
    preventing unintended cancellations or accidental modifications.
    """
    while True:
        try:
            prompt_text = (
                "\n[bold yellow]¿Autorizas la inyección de esta configuración en el equipo? [s=Sí / n=No][/bold yellow]"
            )
            raw = Prompt.ask(prompt_text).strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Interrupción detectada. Operación cancelada por seguridad.[/yellow]")
            return False

        if raw in AFFIRMATIVE_RESPONSES:
            return True
        elif raw in NEGATIVE_RESPONSES:
            return False
        else:
            console.print(
                f"[bold red][!] Respuesta no reconocida: '[white]{raw}[/white]'.[/bold red] "
                f"Por favor ingresa [bold green]'s'[/bold green] (Sí, autorizar) o "
                f"[bold red]'n'[/bold red] (No, rechazar/cancelar)."
            )


def prompt_confirm(prompt_text: str, default: Optional[bool] = None) -> bool:
    """Bilingual confirmation prompt that continuously re-prompts on invalid input."""
    suffix = "[s/n]"
    if default is True:
        suffix = "[S/n]"
    elif default is False:
        suffix = "[s/N]"

    while True:
        try:
            raw = Prompt.ask(f"{prompt_text} [dim]{suffix}[/dim]").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Interrupción detectada.[/yellow]")
            return False if default is None else default

        if not raw and default is not None:
            return default

        if raw in AFFIRMATIVE_RESPONSES:
            return True
        elif raw in NEGATIVE_RESPONSES:
            return False
        else:
            console.print(
                f"[bold red][!] Opción no válida: '[white]{raw}[/white]'.[/bold red] "
                f"Por favor ingresa [bold green]'s'[/bold green] para Sí o "
                f"[bold red]'n'[/bold red] para No."
            )


def prompt_choice(prompt_text: str, choices: List[str], default: Optional[str] = None) -> str:
    """Prompts user to select from a list of choices. Continuously re-prompts if choice is invalid."""
    normalized_choices = [c.strip() for c in choices]
    while True:
        try:
            raw = Prompt.ask(
                prompt_text,
                default=default,
            ).strip()
        except (KeyboardInterrupt, EOFError):
            if default:
                return default
            raise

        if not raw and default is not None:
            return default

        if raw in normalized_choices:
            return raw
        else:
            valid_opts = ", ".join([f"'{c}'" for c in normalized_choices])
            console.print(
                f"[bold red][!] Opción no válida: '[white]{raw}[/white]'.[/bold red] "
                f"Por favor, selecciona una de las opciones disponibles: [bold cyan]{valid_opts}[/bold cyan]."
            )


def prompt_non_empty(prompt_text: str, default: Optional[str] = None, password: bool = False) -> str:
    """Prompts user for non-empty text input. Re-prompts if empty or whitespace-only."""
    while True:
        try:
            raw = Prompt.ask(prompt_text, default=default, password=password)
            if raw is not None:
                val = raw.strip()
                if val:
                    return val
                elif default:
                    return default
        except (KeyboardInterrupt, EOFError):
            if default:
                return default
            raise

        console.print("[bold red][!] Este campo es obligatorio y no puede estar vacío.[/bold red]")


def prompt_int_range(prompt_text: str, min_val: int, max_val: int, default: Optional[int] = None) -> int:
    """Prompts for an integer within a specific range, re-prompting on invalid values."""
    while True:
        try:
            raw = Prompt.ask(prompt_text, default=str(default) if default is not None else None).strip()
            if not raw and default is not None:
                return default
            num = int(raw)
            if min_val <= num <= max_val:
                return num
            else:
                console.print(
                    f"[bold red][!] El número {num} está fuera de rango.[/bold red] "
                    f"Debe estar entre [bold cyan]{min_val}[/bold cyan] y [bold cyan]{max_val}[/bold cyan]."
                )
        except ValueError:
            console.print(
                f"[bold red][!] Entrada inválida.[/bold red] Por favor ingresa un número entero entre "
                f"[bold cyan]{min_val}[/bold cyan] y [bold cyan]{max_val}[/bold cyan]."
            )
        except (KeyboardInterrupt, EOFError):
            if default is not None:
                return default
            raise
