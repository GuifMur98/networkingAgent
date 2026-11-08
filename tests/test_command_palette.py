"""Unit and integration tests for NetworkAgentCommandProvider and the Command Palette."""

import re

import pytest
from textual.command import CommandPalette, SearchIcon
from textual.widgets import Footer, TabbedContent, TextArea

from networking_agent.core.db import db
from networking_agent.tui.app import NetworkingAgentTUIApp
from networking_agent.tui.commands import NetworkAgentCommandProvider

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f700-\U0001f77f"  # alchemical symbols
    "\U0001f780-\U0001f7ff"  # geometric shapes
    "\U0001f800-\U0001f8ff"  # arrows
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "\U0001fa00-\U0001faff"  # symbols & pictographs extended
    "\U00002600-\U000026ff"  # misc symbols
    "\U00002700-\U000027bf"  # dingbats
    "]+",
    flags=re.UNICODE,
)


def test_command_catalog_integrity_and_no_emojis():
    """All commands in the provider must have matching actions on the App and ZERO emojis."""
    assert len(NetworkAgentCommandProvider.COMMANDS) >= 15

    for cmd in NetworkAgentCommandProvider.COMMANDS:
        # Check action exists on app
        action_fn = getattr(NetworkingAgentTUIApp, f"action_{cmd.action_name}", None)
        assert action_fn is not None, f"App is missing action_{cmd.action_name} for command '{cmd.name}'"

        # Check no emojis in name or help
        assert not EMOJI_PATTERN.search(cmd.name), f"Found emoji in command name: {cmd.name}"
        assert not EMOJI_PATTERN.search(cmd.help_text), f"Found emoji in help_text: {cmd.help_text}"
        assert not EMOJI_PATTERN.search(cmd.keywords), f"Found emoji in keywords: {cmd.keywords}"


@pytest.mark.anyio
async def test_command_provider_discover_and_search(tmp_path, monkeypatch):
    """Test discovery hits and fuzzy search in NetworkAgentCommandProvider."""
    app = NetworkingAgentTUIApp()
    async with app.run_test():
        provider = NetworkAgentCommandProvider(app.screen)

        # 1. Test discover yields all commands
        discover_hits = [hit async for hit in provider.discover()]
        assert len(discover_hits) == len(NetworkAgentCommandProvider.COMMANDS)
        names = [str(h.display) for h in discover_hits]
        assert "Navegar: Inicio (Dashboard Principal)" in names
        assert "Equipos: Registrar Nuevo Dispositivo en Catalogo" in names
        assert "Seguridad: Alternar Modo Guardarrailes (HITL / Auto-Aprobacion)" in names

        # 2. Test search by direct title match
        ping_hits = [hit async for hit in provider.search("ping")]
        assert len(ping_hits) > 0
        assert any("Ping" in str(h.prompt) for h in ping_hits)

        # 3. Test search by keywords
        hitl_hits = [hit async for hit in provider.search("hitl")]
        assert len(hitl_hits) > 0
        assert any("Guardarrailes" in str(h.prompt) for h in hitl_hits)

        # 4. Test search by help text / concept
        json_hits = [hit async for hit in provider.search("json")]
        assert len(json_hits) > 0
        assert any("Auditoria" in str(h.prompt) for h in json_hits)


@pytest.mark.anyio
async def test_palette_opens_and_hides_search_icon(tmp_path, monkeypatch):
    """Opening palette via ctrl+p must show CommandPalette with SearchIcon hidden via CSS."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")
        await pilot.pause()

        assert isinstance(app.screen, CommandPalette)
        palette = app.screen
        icon = palette.query_one(SearchIcon)
        assert icon.styles.display == "none"

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, CommandPalette)


@pytest.mark.anyio
async def test_palette_action_navigation(tmp_path, monkeypatch):
    """Executing navigation command from palette switches active tab cleanly."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        tabs = app.query_one("#main-tabs", TabbedContent)
        assert tabs.active == "pane-home"

        # Open palette, type inventario, press enter
        await pilot.press("ctrl+p")
        await pilot.pause()
        await pilot.press("i", "n", "v", "e", "n", "t", "a", "r", "i", "o")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert tabs.active == "pane-inventory"


@pytest.mark.anyio
async def test_palette_action_toggle_hitl(tmp_path, monkeypatch):
    """Executing toggle_hitl command flips guardrail approval mode."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        initial_mode = db.get_setting("auto_approve") == "true"

        # Open palette, search toggle, press enter
        await pilot.press("ctrl+p")
        await pilot.pause()
        await pilot.press("t", "o", "g", "g", "l", "e")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        new_mode = db.get_setting("auto_approve") == "true"
        assert new_mode != initial_mode


@pytest.mark.anyio
async def test_palette_action_symptom_preset(tmp_path, monkeypatch):
    """Executing symptom preset command populates troubleshooting symptom text area."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")
        await pilot.pause()
        await pilot.press("b", "g", "p")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        tabs = app.query_one("#main-tabs", TabbedContent)
        assert tabs.active == "pane-troubleshooting"

        input_box = app.query_one("#symptom-input", TextArea)
        assert "BGP" in input_box.text


@pytest.mark.anyio
async def test_footer_palette_position_and_module_filtering(tmp_path, monkeypatch):
    """Verifies that ^p Paleta is docked on the bottom right and modules display ONLY 'h' Inicio."""
    app = NetworkingAgentTUIApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        tabs = app.query_one("#main-tabs", TabbedContent)

        # 1. On Home dashboard
        home_keys = [c.key for c in footer.query("FooterKey") if "-command-palette" not in c.classes]
        home_palette = [c.key for c in footer.query("FooterKey") if "-command-palette" in c.classes]
        assert home_keys == ["h", "q", "d", "s", "r"]
        assert home_palette == ["ctrl+p"]

        # 2. On Modules, ONLY 'h' is displayed in footer
        for mod in [
            "pane-troubleshooting",
            "pane-configuration",
            "pane-automation",
            "pane-inventory",
            "pane-audit",
        ]:
            tabs.active = mod
            await pilot.pause()
            mod_keys = [c.key for c in footer.query("FooterKey") if "-command-palette" not in c.classes]
            mod_palette = [c.key for c in footer.query("FooterKey") if "-command-palette" in c.classes]
            assert mod_keys == ["h"]
            assert mod_palette == []

        # 3. Pressing 'h' from a module returns to home and restores full footer
        await pilot.press("h")
        await pilot.pause()
        assert tabs.active == "pane-home"
        restored_keys = [c.key for c in footer.query("FooterKey") if "-command-palette" not in c.classes]
        restored_palette = [c.key for c in footer.query("FooterKey") if "-command-palette" in c.classes]
        assert restored_keys == ["h", "q", "d", "s", "r"]
        assert restored_palette == ["ctrl+p"]
