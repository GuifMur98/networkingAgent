"""Automation workspace widget with interactive TextArea editor, dry-run syntax validator, and batch deployment."""

from typing import Dict, List, Optional

from rich import box
from rich.panel import Panel
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Log, ProgressBar, Select, SelectionList, Static, TextArea

from networking_agent.core.db import db
from networking_agent.engine.automation import TemplateEngine
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.models.config_intent import AutomationTemplate
from networking_agent.models.device import DeviceInventory
from networking_agent.tui.modals.template_modal import TemplateModal


class AutomationView(Widget):
    """Full automation suite with interactive text editor, syntax checking, and multi-host deployment."""

    class RunBatchDeploymentRequested(Message):
        """Emitted when the operator requests mass deployment of the editor content."""

        def __init__(self, devices: List[DeviceInventory], script_content: str, vendor_family: str):
            super().__init__()
            self.devices = devices
            self.script_content = script_content
            self.vendor_family = vendor_family

    class ReturnHomeRequested(Message):
        """Emitted when returning to the home screen."""

    VENDOR_CHOICES = [
        ("Cisco IOS / IOS-XE", "cisco_ios"),
        ("Cisco NX-OS", "cisco_nxos"),
        ("Juniper Junos", "juniper_junos"),
        ("MikroTik RouterOS", "mikrotik_routeros"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.templates: List[AutomationTemplate] = TemplateEngine.get_templates()
        self.available_devices: List[DeviceInventory] = []
        self.active_template_raw: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="automation-container"):
            with Vertical(id="automation-content-wrapper", classes="workspace-content-wrapper"):
                # 1. Header Navigation Bar
                with Horizontal(id="automation-top-bar"):
                    yield Label("AUTOMATIZACION // GESTOR DE PLANTILLAS Y DESPLIEGUE MASIVO", id="automation-title")
                    yield Button("Volver al Inicio", id="btn-back-from-automation")

                # 2. Template Catalog & Selection Bar (Sleek horizontal panel)
                with Horizontal(id="automation-toolbar", classes="section-panel"):
                    with Horizontal(id="automation-selectors-row"):
                        with Horizontal(classes="auto-field-pair"):
                            yield Label("Plantilla:", id="lbl-tpl-picker", classes="auto-field-label")
                            template_options = [(t.name, t.name) for t in self.templates] + [
                                ("Script Personalizado / Directo", "custom")
                            ]
                            init_val = self.templates[0].name if self.templates else "custom"
                            yield Select(
                                template_options,
                                value=init_val,
                                id="select-template",
                                allow_blank=False,
                            )

                        with Horizontal(classes="auto-field-pair"):
                            yield Label("Fabricante:", id="lbl-vendor-picker", classes="auto-field-label")
                            init_vendor = self.templates[0].vendor_family if self.templates else "cisco_ios"
                            yield Select(
                                self.VENDOR_CHOICES,
                                value=init_vendor,
                                id="select-vendor-auto",
                                allow_blank=False,
                            )

                    with Horizontal(id="tpl-crud-buttons"):
                        yield Button("+ Nueva", id="btn-new-template", classes="chip-btn")
                        yield Button("Guardar", id="btn-save-template", classes="chip-btn")
                        yield Button("Eliminar", id="btn-delete-template", classes="chip-btn")

                # 3. Dynamic Variables Card (Only displayed when template has variables)
                with Vertical(id="tpl-variables-card", classes="section-panel"):
                    with Horizontal(id="tpl-vars-header"):
                        yield Label("PARÁMETROS DINÁMICOS DE LA PLANTILLA (JINJA2):", id="lbl-tpl-vars")
                        yield Button(
                            "Renderizar a Editor",
                            id="btn-render-variables",
                            variant="primary",
                        )
                    with Vertical(id="tpl-vars-form"):
                        yield Label("", id="lbl-tpl-vars-empty")

                # 4. Main Workspace Split (Left: Editor | Right: Targets & Diagnostic)
                with Horizontal(id="automation-split"):
                    with Vertical(id="editor-col"):
                        yield Label(
                            "Script de Configuración CLI a Inyectar (Editable):",
                            id="lbl-editor",
                        )
                        initial_text = self.templates[0].template_content if self.templates else ""
                        self.active_template_raw = initial_text
                        yield TextArea(
                            text=initial_text,
                            id="automation-editor",
                            language="yaml",
                            show_line_numbers=True,
                        )

                    with Vertical(id="devices-and-status-col"):
                        with Horizontal(id="devices-header-row"):
                            yield Label("Equipos Destino para Despliegue:", id="lbl-target-devices")
                            yield Button("Todos", id="btn-select-all-devices", classes="chip-btn")
                            yield Button("Ninguno", id="btn-deselect-all-devices", classes="chip-btn")

                        yield SelectionList[str](id="device-selection-list")

                        yield Label("Diagnóstico de Sintaxis y Seguridad (Dry-Run):", id="lbl-syntax-header")
                        yield Static(id="syntax-status-card")

                # 5. Action Trigger Row
                with Horizontal(id="automation-actions"):
                    yield Button("Validar Sintaxis (Dry-Run)", id="btn-validate-script")
                    yield Button("Ejecutar Despliegue en Lote", id="btn-deploy-batch", variant="primary")

                # 6. Live Telemetry & Execution Log Terminal (Unified progress header)
                with Vertical(id="auto-progress-container"):
                    with Horizontal(id="auto-progress-header"):
                        yield Label(
                            "Consola de Despliegue Masivo y Rollback por Lote:",
                            id="lbl-auto-console",
                        )
                        yield Label("[dim]Listo para validación o despliegue en lote[/dim]", id="lbl-auto-step")
                        yield Label("[bold #00e5ff]0%[/]", id="lbl-auto-pct")
                    yield ProgressBar(id="auto-progress-bar", total=100.0, show_eta=False, show_percentage=False)

                yield Log(id="automation-log-terminal", highlight=True)

    def on_mount(self) -> None:
        self.reload_devices()
        self._refresh_variable_panel()
        self._run_syntax_validation()

    def reload_templates(self, select_name: Optional[str] = None) -> None:
        """Refreshes the template catalog from database and updates select dropdown."""
        self.templates = TemplateEngine.get_templates()
        template_select = self.query_one("#select-template", Select)
        options = [(t.name, t.name) for t in self.templates] + [("Script Personalizado / Directo", "custom")]

        template_select.set_options(options)
        target = select_name or (self.templates[0].name if self.templates else "custom")
        template_select.value = target

    def reload_devices(self) -> None:
        """Loads available devices from SQLite into the checklist."""
        raw_devs = db.list_devices()
        self.available_devices = []
        selection_list = self.query_one("#device-selection-list", SelectionList)
        selection_list.clear_options()

        for idx, dev_dict in enumerate(raw_devs):
            dev = db.get_device_by_id(dev_dict["id"])
            if dev:
                self.available_devices.append(dev)
                label = f"{dev.host} ({dev.device_type}) [{dev.username}]"
                initial_val = idx == 0
                selection_list.add_option((label, dev.host, initial_val))

    def update_progress(self, percent: float, step_label: str) -> None:
        """Updates live deployment progress bar and step labels."""
        import threading

        def _apply():
            try:
                pbar = self.query_one("#auto-progress-bar", ProgressBar)
                lbl_step = self.query_one("#lbl-auto-step", Label)
                lbl_pct = self.query_one("#lbl-auto-pct", Label)
                pbar.update(progress=percent)
                lbl_step.update(step_label)
                color = "#4ade80" if percent >= 100 else "#00e5ff"
                lbl_pct.update(f"[bold {color}]{int(percent)}%[/]")
            except Exception:
                pass

        try:
            if self.app and threading.current_thread() is not threading.main_thread():
                self.app.call_from_thread(_apply)
            else:
                _apply()
        except Exception:
            _apply()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-template":
            chosen = str(event.value)
            editor = self.query_one("#automation-editor", TextArea)
            vendor_select = self.query_one("#select-vendor-auto", Select)

            if chosen == "custom":
                self.active_template_raw = editor.text
                self._refresh_variable_panel()
                self._run_syntax_validation()
                return

            for tpl in self.templates:
                if tpl.name == chosen:
                    self.active_template_raw = tpl.template_content
                    editor.text = tpl.template_content
                    vendor_select.value = tpl.vendor_family
                    self._refresh_variable_panel()
                    self._run_syntax_validation()
                    break

        elif event.select.id == "select-vendor-auto":
            self._run_syntax_validation()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back-from-automation":
            self.post_message(self.ReturnHomeRequested())
        elif event.button.id == "btn-validate-script":
            self._run_syntax_validation()
        elif event.button.id == "btn-deploy-batch":
            self._trigger_batch_deployment()
        elif event.button.id == "btn-new-template":
            self._open_new_template_modal()
        elif event.button.id == "btn-save-template":
            self._open_save_template_modal()
        elif event.button.id == "btn-delete-template":
            self._delete_current_template()
        elif event.button.id == "btn-render-variables":
            self._render_variables_to_editor()
        elif event.button.id == "btn-select-all-devices":
            self._set_all_devices_selection(True)
        elif event.button.id == "btn-deselect-all-devices":
            self._set_all_devices_selection(False)

    def _set_all_devices_selection(self, selected: bool) -> None:
        selection_list = self.query_one("#device-selection-list", SelectionList)
        for opt in self.available_devices:
            if selected:
                selection_list.select(opt.host)
            else:
                selection_list.deselect(opt.host)

    def _open_new_template_modal(self) -> None:
        """Opens template creation modal."""
        curr_vendor = str(self.query_one("#select-vendor-auto", Select).value)

        def _on_created(created_tpl: Optional[AutomationTemplate]) -> None:
            if created_tpl:
                self.reload_templates(select_name=created_tpl.name)
                self.append_log(f"[green][OK] Plantilla '{created_tpl.name}' creada exitosamente.[/green]")

        self.app.push_screen(TemplateModal(initial_vendor=curr_vendor), _on_created)

    def _open_save_template_modal(self) -> None:
        """Opens modal prefilled with current editor content to save or update."""
        editor = self.query_one("#automation-editor", TextArea)
        curr_vendor = str(self.query_one("#select-vendor-auto", Select).value)
        curr_name = str(self.query_one("#select-template", Select).value)
        match_tpl = next((t for t in self.templates if t.name == curr_name), None)

        def _on_saved(saved_tpl: Optional[AutomationTemplate]) -> None:
            if saved_tpl:
                self.reload_templates(select_name=saved_tpl.name)
                self.append_log(f"[green][OK] Plantilla '{saved_tpl.name}' guardada correctamente.[/green]")

        self.app.push_screen(
            TemplateModal(
                template=match_tpl,
                initial_content=editor.text,
                initial_vendor=curr_vendor,
            ),
            _on_saved,
        )

    def _delete_current_template(self) -> None:
        """Removes the active custom template from database."""
        chosen = str(self.query_one("#select-template", Select).value)
        if chosen == "custom":
            self.append_log("[yellow]Aviso: No se puede eliminar el script personalizado.[/yellow]")
            return

        success = TemplateEngine.delete_custom_template(chosen)
        if success:
            self.append_log(f"[green][OK] Plantilla personalizada '{chosen}' eliminada.[/green]")
            self.reload_templates()
        else:
            self.append_log(
                f"[yellow]Aviso: La plantilla '{chosen}' es del sistema y está protegida contra borrado.[/yellow]"
            )

    def _refresh_variable_panel(self) -> None:
        """Dynamically renders variable inputs for detected template parameters in clean pairs."""
        vars_card = self.query_one("#tpl-variables-card", Vertical)
        form_container = self.query_one("#tpl-vars-form", Vertical)
        form_container.remove_children()

        chosen_name = str(self.query_one("#select-template", Select).value)
        current_tpl = next((t for t in self.templates if t.name == chosen_name), None)

        vars_list = TemplateEngine.extract_variables(self.active_template_raw)
        defaults: Dict[str, str] = current_tpl.parameters_schema if current_tpl else {}

        if not vars_list:
            vars_card.display = False
            return

        vars_card.display = True

        rows = []
        for i in range(0, len(vars_list), 2):
            pair = vars_list[i : i + 2]
            fields = []
            for var_name in pair:
                default_val = str(defaults.get(var_name, ""))
                lbl = Label(f"{var_name}:", classes="tpl-var-label")
                inp = Input(
                    value=default_val,
                    placeholder=f"Valor para {var_name}",
                    id=f"var-inp-{var_name}",
                )
                fields.append(Horizontal(lbl, inp, classes="tpl-var-field-group"))
            if len(pair) == 1:
                fields.append(Horizontal(classes="tpl-var-field-group-spacer"))
            rows.append(Horizontal(*fields, classes="tpl-vars-form-row"))

        if rows:
            form_container.mount(*rows)

    def _render_variables_to_editor(self) -> None:
        """Collects parameter inputs and renders the template into the editor."""
        vars_list = TemplateEngine.extract_variables(self.active_template_raw)
        if not vars_list:
            self.append_log("[yellow]Aviso: No hay variables {{ }} que renderizar en esta plantilla.[/yellow]")
            return

        var_values: Dict[str, str] = {}
        for var_name in vars_list:
            try:
                inp = self.query_one(f"#var-inp-{var_name}", Input)
                var_values[var_name] = inp.value.strip()
            except Exception:
                var_values[var_name] = ""

        # Check for unpopulated variables
        empty_vars = [k for k, v in var_values.items() if not v]
        if empty_vars:
            vars_joined = ", ".join(empty_vars)
            self.append_log(
                f"[bold red][!] Ingrese los valores para las siguientes variables antes de renderizar: {vars_joined}[/]"
            )
            return

        try:
            rendered = TemplateEngine.render(self.active_template_raw, var_values)
            editor = self.query_one("#automation-editor", TextArea)
            editor.text = rendered
            self.append_log(
                f"[bold green][OK] {len(var_values)} variables renderizadas exitosamente en el editor.[/bold green]"
            )
            self._run_syntax_validation()
        except Exception as e:
            self.append_log(f"[bold red][!] Error al renderizar plantilla: {e}[/bold red]")

    def _run_syntax_validation(self) -> None:
        """Performs static syntax and guardrail analysis on the editor content."""
        editor = self.query_one("#automation-editor", TextArea)
        vendor_family = str(self.query_one("#select-vendor-auto", Select).value)
        status_card = self.query_one("#syntax-status-card", Static)

        report = ConfigSyntaxValidator.validate_script(editor.text, vendor_family=vendor_family)

        if report.is_valid:
            warn_text = (
                "\n\n[bold yellow]Avisos y Recomendaciones:[/bold yellow]\n"
                + "\n".join([f"  * {w}" for w in report.warnings])
                if report.warnings
                else ""
            )
            content = (
                f"[bold green][OK] SINTAXIS VALIDA (DRY-RUN EXITOSO)[/bold green]\n"
                f"  * Comandos identificados: {report.line_count}\n"
                f"  * Fabricante: {vendor_family}\n"
                f"  * Guardarraíles destructivos: 0 violaciones{warn_text}\n\n"
                f"[dim]El script cumple con los requisitos del SO y está listo para desplegar.[/dim]"
            )
            panel = Panel(content, title="ANALISIS ESTATICO OS", border_style="#4ade80", box=box.ROUNDED)
        else:
            err_text = "\n".join([f"  * {err}" for err in report.errors])
            warn_text = (
                "\n\n[yellow]Avisos:[/yellow]\n" + "\n".join([f"  * {w}" for w in report.warnings])
                if report.warnings
                else ""
            )
            content = (
                f"[bold red][!] ERRORES DE SINTAXIS O SEGURIDAD DETECTADOS[/bold red]\n"
                f"{err_text}{warn_text}\n\n"
                f"[dim]Corrija los errores indicados antes de proceder al despliegue.[/dim]"
            )
            panel = Panel(content, title="BLOQUEO DE SEGURIDAD OS", border_style="#f43f5e", box=box.ROUNDED)

        status_card.update(panel)

    def _trigger_batch_deployment(self) -> None:
        """Collects selected targets and dispatches deployment message."""
        selection_list = self.query_one("#device-selection-list", SelectionList)
        selected_hosts = selection_list.selected

        if not selected_hosts:
            self.append_log("[bold red][!] Selecciona al menos un equipo de la lista para el despliegue.[/]")
            return

        targets = [d for d in self.available_devices if d.host in selected_hosts]
        editor = self.query_one("#automation-editor", TextArea)
        vendor_family = str(self.query_one("#select-vendor-auto", Select).value)

        # Validate syntax first
        report = ConfigSyntaxValidator.validate_script(editor.text, vendor_family=vendor_family)
        if not report.is_valid:
            self.append_log("[bold red][!] Corrige primero los errores de sintaxis antes de desplegar.[/]")
            return

        self.post_message(
            self.RunBatchDeploymentRequested(
                devices=targets,
                script_content=editor.text,
                vendor_family=vendor_family,
            )
        )

    def append_log(self, text: str) -> None:
        """Appends log lines to the batch log pane."""
        log = self.query_one("#automation-log-terminal", Log)
        try:
            from rich.text import Text

            log.write_line(Text.from_markup(text))
        except Exception:
            log.write_line(text)
