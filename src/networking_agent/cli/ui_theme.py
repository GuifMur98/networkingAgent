"""UI Themes, Visual Banners and Stepper Components for Rich CLI Experience."""

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from networking_agent.core.logging import console


def print_main_banner() -> None:
    """Displays the stylish main header banner."""
    title_text = Text()
    title_text.append("🌐  N E T W O R K I N G   A G E N T   E N T E R P R I S E\n", style="bold cyan")
    title_text.append("Autonomous & Closed-Loop Network Reliability Engineering Platform\n", style="bold white")
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
        title="📋 Resumen del Plan de Diagnóstico",
        show_header=True,
        header_style="bold cyan",
        border_style="bright_blue",
    )
    summary_table.add_column("Componente", style="bold white", width=22)
    summary_table.add_column("Detalle Configurado", style="green")

    summary_table.add_row("🧠 Cerebro de IA", f"{provider.upper()} ({model})")
    summary_table.add_row("🔌 Dispositivo Destino", f"{device_host} [{device_type}] (Usuario: {device_user})")
    summary_table.add_row(
        "🔍 Modo de Operación", f"[{'bold magenta' if mode == 'PROACTIVE' else 'bold yellow'}]{mode}[/]"
    )
    summary_table.add_row(
        "📄 Telemetría / Síntoma", symptom_summary[:90] + ("..." if len(symptom_summary) > 90 else "")
    )

    console.print(summary_table)
