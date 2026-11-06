"""Unit tests for the robust validated CLI interactive prompt helpers."""

from networking_agent.cli.prompts import (
    prompt_choice,
    prompt_confirm,
    prompt_hitl_approval,
    prompt_int_range,
    prompt_non_empty,
)


def test_prompt_hitl_approval_accepts_valid_and_repairs_invalid(mocker):
    # First enters invalid 'maybe', then 'foo', then valid 'si'
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["maybe", "foo", "si"])
    assert prompt_hitl_approval() is True
    assert mock_ask.call_count == 3


def test_prompt_hitl_approval_accepts_rejection_after_typo(mocker):
    # First enters typo 'nono', then enters valid 'n'
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["nono", "n"])
    assert prompt_hitl_approval() is False
    assert mock_ask.call_count == 2


def test_prompt_hitl_approval_handles_interrupt(mocker):
    mocker.patch("rich.prompt.Prompt.ask", side_effect=KeyboardInterrupt)
    assert prompt_hitl_approval() is False


def test_prompt_confirm_reprompts_until_valid(mocker):
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["bad_answer", "s"])
    assert prompt_confirm("¿Continuar?", default=False) is True
    assert mock_ask.call_count == 2


def test_prompt_confirm_uses_default_on_empty(mocker):
    mocker.patch("rich.prompt.Prompt.ask", return_value="")
    assert prompt_confirm("¿Guardar?", default=True) is True
    assert prompt_confirm("¿Guardar?", default=False) is False


def test_prompt_choice_reprompts_until_in_choices(mocker):
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["9", "abc", "2"])
    res = prompt_choice("Selecciona opción", choices=["1", "2", "3"])
    assert res == "2"
    assert mock_ask.call_count == 3


def test_prompt_non_empty_reprompts_until_non_whitespace(mocker):
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["", "   ", "valid_host"])
    res = prompt_non_empty("Ingresa host")
    assert res == "valid_host"
    assert mock_ask.call_count == 3


def test_prompt_int_range_reprompts_on_invalid_and_out_of_range(mocker):
    mock_ask = mocker.patch("rich.prompt.Prompt.ask", side_effect=["not_a_number", "99999", "22"])
    res = prompt_int_range("Puerto SSH", min_val=1, max_val=65535)
    assert res == 22
    assert mock_ask.call_count == 3
