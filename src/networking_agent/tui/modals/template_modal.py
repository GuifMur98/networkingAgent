"""Modal screen for creating and managing reusable configuration templates."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, TextArea

from networking_agent.engine.automation import TemplateEngine
from networking_agent.models.config_intent import AutomationTemplate


class TemplateModal(ModalScreen[Optional[AutomationTemplate]]):
    """Dialog screen for defining and saving parameterized Jinja2 configuration templates."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    VENDOR_CHOICES = [
        ("Cisco IOS / IOS-XE", "cisco_ios"),
        ("Cisco NX-OS", "cisco_nxos"),
        ("Juniper Junos", "juniper_junos"),
        ("MikroTik RouterOS", "mikrotik_routeros"),
    ]

    COMMON_VARIABLES = [
        "vlan_id",
        "vlan_name",
        "ip_address",
        "netmask",
        "gateway",
        "interface",
        "description",
        "bgp_as",
    ]

    def __init__(
        self,
        template: Optional[AutomationTemplate] = None,
        initial_content: Optional[str] = None,
        initial_vendor: str = "cisco_ios",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.editing_template = template
        self.initial_content = initial_content or (template.template_content if template else "")
        self.initial_vendor = template.vendor_family if template else initial_vendor

    def compose(self) -> ComposeResult:
        title_text = (
            "EDITAR PLANTILLA DE AUTOMATIZACION"
            if self.editing_template
            else "NUEVA PLANTILLA DE CONFIGURACION"
        )
        with Vertical(classes="modal-dialog", id="template-modal-dialog"):
            yield Label(title_text, classes="modal-title")

            with Horizontal(classes="tpl-modal-row-split"):
                with Vertical(classes="tpl-modal-col-name"):
                    yield Label("Nombre de la Plantilla:")
                    init_name = self.editing_template.name if self.editing_template else ""
                    yield Input(placeholder="Ej: OSPF Multi-Área LAN", value=init_name, id="input-tpl-name")
                with Vertical(classes="tpl-modal-col-vendor"):
                    yield Label("Fabricante / Sistema Operativo:")
                    yield Select(
                        self.VENDOR_CHOICES,
                        value=self.initial_vendor,
                        id="select-tpl-vendor",
                        allow_blank=False,
                    )

            with Vertical(classes="modal-row-full"):
                yield Label("Descripción Operativa:")
                init_desc = self.editing_template.description if self.editing_template else ""
                yield Input(
                    placeholder="Propósito técnico y alcance de la plantilla...",
                    value=init_desc,
                    id="input-tpl-desc",
                )

            # Guía interactiva de sintaxis Jinja2 y atajos de inserción
            with Vertical(classes="tpl-guide-card"):
                with Horizontal(id="tpl-guide-header"):
                    yield Label("GUIA DE VARIABLES DINAMICAS (JINJA2):", id="lbl-guide-title")
                    yield Label("Sintaxis: {{ nombre_variable }}", id="lbl-guide-syntax")
                yield Label(
                    "Encierra cualquier parámetro en dobles llaves para volverlo dinámico. "
                    "El motor solicitará los valores al ejecutar despliegues masivos.",
                    id="lbl-guide-desc",
                )
                with Horizontal(id="tpl-chips-row"):
                    yield Label("Atajos (clic para insertar):", id="lbl-chips-tag")
                    for var in self.COMMON_VARIABLES:
                        yield Button(var, id=f"chip-var-{var}", classes="tpl-var-chip")

            with Vertical(classes="modal-row-full", id="modal-editor-row"):
                with Horizontal(id="modal-editor-header"):
                    yield Label("Contenido CLI con Sintaxis Jinja2:", id="lbl-modal-editor")
                    yield Button("Detectar Variables", id="btn-detect-vars", classes="chip-btn")

                yield TextArea(
                    text=self.initial_content,
                    id="input-tpl-content",
                    language="yaml",
                    show_line_numbers=True,
                )

            yield Label("", id="lbl-tpl-feedback", classes="error-label")

            with Horizontal(classes="modal-actions"):
                yield Button("Guardar Plantilla", id="btn-save-tpl", variant="primary")
                yield Button("Cancelar", id="btn-cancel-tpl")

    def on_mount(self) -> None:
        """Trigger initial variable scan if initial content is present."""
        self.action_detect_variables()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Live updates variable detection as the user edits the template content."""
        if event.text_area.id == "input-tpl-content":
            self.action_detect_variables()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-tpl":
            self.action_save()
        elif event.button.id == "btn-cancel-tpl":
            self.action_cancel()
        elif event.button.id == "btn-detect-vars":
            self.action_detect_variables()
        elif event.button.id and event.button.id.startswith("chip-var-"):
            var_name = event.button.id.replace("chip-var-", "")
            self._insert_variable(var_name)

    def _insert_variable(self, var_name: str) -> None:
        """Inserts {{ var_name }} into the template editor at the cursor location."""
        editor = self.query_one("#input-tpl-content", TextArea)
        editor.insert(f"{{{{ {var_name} }}}}")
        editor.focus()

    def action_detect_variables(self) -> None:
        """Parses the text area content and reports variables found in real time."""
        try:
            editor = self.query_one("#input-tpl-content", TextArea)
            feedback = self.query_one("#lbl-tpl-feedback", Label)
        except Exception:
            return

        vars_found = TemplateEngine.extract_variables(editor.text)
        if vars_found:
            vars_str = ", ".join(vars_found)
            feedback.update(
                f"[bold cyan]Variables detectadas ({len(vars_found)}):[/bold cyan] [bold white]{vars_str}[/bold white]"
            )
        else:
            if editor.text.strip():
                feedback.update(
                    "[dim cyan]Script directo (sin variables). Usa {{ variable }} para parametrizar.[/dim cyan]"
                )
            else:
                feedback.update("")

    def action_save(self) -> None:
        """Validates and persists the template."""
        name = self.query_one("#input-tpl-name", Input).value.strip()
        vendor = str(self.query_one("#select-tpl-vendor", Select).value)
        desc = self.query_one("#input-tpl-desc", Input).value.strip()
        content = self.query_one("#input-tpl-content", TextArea).text
        feedback = self.query_one("#lbl-tpl-feedback", Label)

        if not name:
            feedback.update("[bold red]Error: El nombre de la plantilla es obligatorio.[/bold red]")
            return

        if not content.strip():
            feedback.update("[bold red]Error: El contenido de la plantilla no puede estar vacío.[/bold red]")
            return

        if not desc:
            desc = f"Plantilla personalizada para {vendor}"

        try:
            saved_tpl = TemplateEngine.save_custom_template(
                name=name,
                vendor_family=vendor,
                description=desc,
                template_content=content,
            )
            self.dismiss(saved_tpl)
        except Exception as e:
            feedback.update(f"[bold red]Error al guardar plantilla: {e}[/bold red]")

    def action_cancel(self) -> None:
        self.dismiss(None)
