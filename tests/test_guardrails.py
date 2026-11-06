"""Unit tests for Guardrails and Blast Radius policies."""

import pytest

from networking_agent.core.exceptions import BlastRadiusViolationError, CommandInjectionError
from networking_agent.guardrails.blast_radius import BlastRadiusGuard
from networking_agent.guardrails.validator import CommandValidator
from networking_agent.models.intent import NetworkIntent


def test_command_validator_accepts_clean_commands():
    clean_cmds = [
        "interface Ethernet1/1",
        "mtu 9216",
        "no shutdown",
    ]
    validated = CommandValidator.validate_command_list(clean_cmds)
    assert validated == clean_cmds


@pytest.mark.parametrize(
    "forbidden_cmd",
    [
        "reload",
        "format flash:",
        "erase startup-config",
        "username attacker privilege 15 secret 0 hacked",
        "no ip routing",
        "crypto key zeroize rsa",
        "interface Gi0/1; reload",
    ],
)
def test_command_validator_blocks_dangerous_commands(forbidden_cmd):
    with pytest.raises(CommandInjectionError):
        CommandValidator.validate_command_list([forbidden_cmd])


@pytest.mark.parametrize("protected_iface", ["Management0", "mgmt0", "GigabitEthernet0/0", "Loopback0"])
def test_blast_radius_guard_protects_critical_interfaces(protected_iface):
    guard = BlastRadiusGuard()
    intent = NetworkIntent(
        diagnosis="Attempting to disable management port",
        severity="CRITICAL",
        requires_config_change=True,
        action="disable_interface",
        target_interface=protected_iface,
    )
    with pytest.raises(BlastRadiusViolationError):
        guard.verify_intent(intent)


def test_blast_radius_guard_allows_safe_interfaces():
    guard = BlastRadiusGuard()
    intent = NetworkIntent(
        diagnosis="Normal edge port modification",
        severity="MEDIUM",
        requires_config_change=True,
        action="set_interface_mtu",
        target_interface="Ethernet1/10",
        mtu_value=9000,
    )
    # Should not raise
    guard.verify_intent(intent)
