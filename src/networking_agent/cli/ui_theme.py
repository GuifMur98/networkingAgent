"""UI Themes, Visual Banners and Stepper Components for Rich CLI Experience."""

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from networking_agent.core.logging import console

ASCII_BANNER = r"""  _   _      _                      _     _               _                    _   
 | \ | | ___| |___      _____  _ __| | __(_)_ __   __ _  / \   __ _  ___ _ __ | |_ 
 |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ /| | '_ \ / _` |/ _ \ / _` |/ _ \ '_ \| __|
 | |\  |  __/ |_ \ V  V / (_) | |  |   < | | | | | (_| / ___ \ (_| |  __/ | | | |_ 
 |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\|_|_| |_|\__, /_/   \_\__, |\___|_| |_|\__|
                                                   |___/        |___/                """

COMPACT_BANNER = r""" _   _      _                      _               _   
| \ | | ___| |___      _____  _ __| | __  /\   ___| |_ 
|  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / /  \ / _ \ __|
| |\  |  __/ |_ \ V  V / (_) | |  |   < / /\ \  __/ |_ 
|_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_/_/  \_\___|\__|"""


def print_main_banner() -> None:
    """Displays the stylish main header banner with ASCII typography and platform metadata."""
    logo = ASCII_BANNER if (console.width or 100) >= 90 else COMPACT_BANNER

    title_text = Text()
    title_text.append(logo + "\n\n", style="bold cyan")
    title_text.append("Enterprise Autonomous Closed-Loop Network Agent\n", style="bold white")
    title_text.append("Cisco • Juniper • MikroTik | Ollama • Gemini • OpenAI • Claude", style="dim italic")

    panel = Panel(
        Align.center(title_text),
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(panel)


def print_step_header(step: int, total: int, title: str, subtitle: str) -> None:
    """Renders a stylish step progress indicator."""
    step_indicator = f"[bold yellow]PASO {step} DE {total}[/bold yellow]"
    header_content = f"{step_indicator} • [bold white]{title}[/bold white]\n[dim]{subtitle}[/dim]"
    console.print(
        Panel(
            header_content,
            border_style="cyan",
            padding=(0, 1),
        )
    )


def print_execution_summary(
    provider: str,
    model: str,
    device_host: str,
    device_type: str,
    device_user: str,
    mode: str,
    symptom_summary: str,
) -> None:
    """Displays a clean summary card of the selected parameters before running."""
    summary_table = Table(
        title="RESUMEN DEL PLAN DE DIAGNOSTICO",
        show_header=True,
        header_style="bold cyan",
        border_style="bright_blue",
    )
    summary_table.add_column("Componente", style="bold white", width=22)
    summary_table.add_column("Detalle Configurado", style="green")

    summary_table.add_row("Cerebro de IA", f"{provider.upper()} ({model})")
    summary_table.add_row("Dispositivo Destino", f"{device_host} [{device_type}] (Usuario: {device_user})")
    summary_table.add_row(
        "Modo de Operacion", f"[{'bold magenta' if mode == 'PROACTIVE' else 'bold yellow'}]{mode}[/]"
    )
    summary_table.add_row(
        "Telemetria / Sintoma", symptom_summary[:90] + ("..." if len(symptom_summary) > 90 else "")
    )

    console.print(summary_table)
