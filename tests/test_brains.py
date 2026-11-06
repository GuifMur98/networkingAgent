"""Unit tests for AI Brain providers including Google Gemini."""

from unittest.mock import MagicMock

import pytest

from networking_agent.brains.factory import get_ai_brain
from networking_agent.brains.gemini import GeminiBrain
from networking_agent.core.exceptions import AIAnalysisError


def test_gemini_brain_initialization_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIAnalysisError, match="GEMINI_API_KEY is not configured"):
        GeminiBrain(api_key=None)


def test_gemini_brain_analyzes_event_successfully(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key_for_testing")

    # Mock response object from google-genai
    mock_response = MagicMock()
    mock_response.text = (
        '{"diagnosis": "MTU mismatch on ether1 causing OSPF failure", '
        '"severity": "HIGH", "requires_config_change": true, '
        '"action": "set_interface_mtu", "target_interface": "ether1", '
        '"mtu_value": 9000, "bgp_neighbor_ip": null}'
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    brain = GeminiBrain(api_key="fake_key")
    brain.client = mock_client

    intent = brain.analyze_event("OSPF error on ether1")
    assert intent.action == "set_interface_mtu"
    assert intent.target_interface == "ether1"
    assert intent.mtu_value == 9000


def test_factory_returns_gemini_brain(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    brain = get_ai_brain(provider="gemini", model="gemini-3.8-flash")
    assert isinstance(brain, GeminiBrain)
    assert brain.model_name == "gemini-3.8-flash"
