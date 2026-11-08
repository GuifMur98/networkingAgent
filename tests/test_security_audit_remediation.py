"""Comprehensive verification suite for Cybersecurity Audit & Ethical Pentest Remediations (v2.1.1).

Validates hotfixes for:
- VULN-01: Server-Side Template Injection (SSTI) in TemplateEngine
- VULN-02: SSH Host Key Verification & MitM Protection in Netmiko
- VULN-03: Command Guardrails Blacklist Extensions (TFTP, SNMP RW, Telnet, default route)
- VULN-04: Master Key Access Control Lists (ACLs) under Windows & POSIX
- VULN-05: CWD Hijacking & Anchored Application Data Directory Resolution
- VULN-06: Sensitive Credential Masking in Audit Logs
- VULN-07: Cryptographic SHA-256 Hash Chaining & Tamper Detection in Audit Trails
- VULN-08: Safe Installer Downloads without blind pipe-to-shell execution
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import paramiko
import pytest

from networking_agent.core.audit import AuditLogger, verify_audit_integrity
from networking_agent.core.config import get_app_data_dir, get_app_log_dir
from networking_agent.core.crypto import secure_file_permissions
from networking_agent.core.exceptions import CommandInjectionError, DeviceConnectionError
from networking_agent.drivers.cisco_ios import CiscoIOSDriver
from networking_agent.engine.automation import TemplateEngine, TemplateSecurityError
from networking_agent.guardrails.syntax_validator import ConfigSyntaxValidator
from networking_agent.guardrails.validator import CommandValidator
from networking_agent.models.device import DeviceInventory


# ==============================================================================
# VULN-01: Server-Side Template Injection (SSTI) Prevention
# ==============================================================================
def test_vuln_01_ssti_prevention_in_template_engine():
    """Verify that Jinja2 SandboxedEnvironment blocks SSTI, introspection, and OS execution."""
    # 1. Cycler dunder introspection payload
    cycler_payload = "{{ cycler.__init__.__globals__['os'].popen('echo VULN_TEST').read() }}"
    with pytest.raises(TemplateSecurityError) as exc_info:
        TemplateEngine.render(cycler_payload, {})
    assert "SSTI or unsafe attribute access detected" in str(exc_info.value)

    # 2. String class traversal payload
    class_payload = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
    with pytest.raises(TemplateSecurityError):
        TemplateEngine.render(class_payload, {})

    # 3. Legitimate network templates still render cleanly
    valid_template = "vlan {{ vlan_id }}\n name {{ vlan_name }}"
    rendered = TemplateEngine.render(valid_template, {"vlan_id": "200", "vlan_name": "SEC_TEST"})
    assert "vlan 200" in rendered
    assert "name SEC_TEST" in rendered


# ==============================================================================
# VULN-02: SSH Host Key Verification & MitM Protection
# ==============================================================================
def test_vuln_02_ssh_host_key_parameters_and_mitm_detection():
    """Verify that DeviceInventory activates system_host_keys and driver handles BadHostKeyException."""
    device = DeviceInventory(
        host="192.168.10.1",
        device_type="cisco_ios",
        username="admin",
        system_host_keys=True,
        ssh_strict=True,
    )
    netmiko_dict = device.to_netmiko_dict()
    assert netmiko_dict["system_host_keys"] is True
    assert netmiko_dict["ssh_strict"] is True

    # Test driver detection of BadHostKeyException
    driver = CiscoIOSDriver(device=device)
    mock_bad_key = MagicMock()
    with patch(
        "networking_agent.drivers.base.ConnectHandler",
        side_effect=paramiko.BadHostKeyException("192.168.10.1", mock_bad_key, mock_bad_key),
    ):
        with pytest.raises(DeviceConnectionError) as exc_info:
            driver.get_connection()
        assert "MitM detectado" in str(exc_info.value)
        assert "no coincide con la registrada en known_hosts" in str(exc_info.value)


# ==============================================================================
# VULN-03: Command Guardrails Blacklist Extensions
# ==============================================================================
@pytest.mark.parametrize(
    "dangerous_cmd",
    [
        "copy tftp://10.10.10.1/malicious.bin running-config",
        "copy ftp://10.0.0.1/boot.bin startup-config",
        "snmp-server community public RW",
        "transport input telnet",
        "transport input all",
        "no service password-encryption",
        "ip route 0.0.0.0 0.0.0.0 192.168.1.254",
        "set routing-options static route 0.0.0.0/0 next-hop 10.0.0.1",
    ],
)
def test_vuln_03_command_validator_blocks_extended_blacklist(dangerous_cmd):
    """Verify that newly identified dangerous command vectors are strictly rejected."""
    with pytest.raises(CommandInjectionError):
        CommandValidator.validate(dangerous_cmd)

    # Also check ConfigSyntaxValidator static report
    report = ConfigSyntaxValidator.validate_script(dangerous_cmd, vendor_family="cisco_ios")
    assert report.is_valid is False
    assert len(report.errors) > 0


# ==============================================================================
# VULN-04: Master Key Access Control Lists (ACLs)
# ==============================================================================
def test_vuln_04_secure_file_permissions(tmp_path):
    """Verify that secure_file_permissions executes without throwing exceptions on the OS."""
    test_key = tmp_path / "test_vault.key"
    test_key.write_text("dummy_fernet_key_data", encoding="utf-8")
    assert test_key.exists()

    # Must execute safely regardless of platform (Windows icacls or POSIX chmod)
    secure_file_permissions(test_key)
    assert test_key.exists()


# ==============================================================================
# VULN-05: CWD Hijacking & Anchored Path Resolution
# ==============================================================================
def test_vuln_05_cwd_hijacking_path_anchoring(tmp_path, monkeypatch):
    """Verify that get_app_data_dir() respects explicit environment variables and avoids relative CWD traps."""
    custom_data_dir = tmp_path / "secure_enterprise_data"
    monkeypatch.setenv("NETWORKING_AGENT_DATA_DIR", str(custom_data_dir))

    resolved_data = get_app_data_dir()
    assert resolved_data == custom_data_dir.resolve()
    assert resolved_data.exists()

    custom_log_dir = tmp_path / "secure_enterprise_logs"
    monkeypatch.setenv("NETWORKING_AGENT_LOG_DIR", str(custom_log_dir))
    resolved_log = get_app_log_dir()
    assert resolved_log == custom_log_dir.resolve()
    assert resolved_log.exists()


# ==============================================================================
# VULN-06: Credential Masking in Audit Logs
# ==============================================================================
def test_vuln_06_credential_masking_in_audit_logger(tmp_path):
    """Verify that passwords, secrets, and SNMP communities are masked before persisting to audit.jsonl."""
    audit_file = tmp_path / "audit_masking_test.jsonl"
    logger = AuditLogger(log_path=audit_file)

    commands_with_secrets = [
        "enable secret HighlySecretEnablePass123",
        "username admin password 0 CleartextPass999",
        "snmp-server community PrivateCorpRW RO",
        "crypto isakmp key VPNPresharedKey123 address 10.0.0.1",
    ]
    raw_output = "Password configured: CleartextPass999, Secret set to HighlySecretEnablePass123"

    logger.record_event(
        event_type="CONFIG_APPLIED",
        device_host="192.168.1.1",
        action="apply_hardening",
        commands=commands_with_secrets,
        approved=True,
        execution_output=raw_output,
    )

    with open(audit_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    assert "HighlySecretEnablePass123" not in log_content
    assert "CleartextPass999" not in log_content
    assert "PrivateCorpRW" not in log_content
    assert "VPNPresharedKey123" not in log_content
    assert "********" in log_content


# ==============================================================================
# VULN-07: Cryptographic SHA-256 Hash Chaining & Tamper Detection
# ==============================================================================
def test_vuln_07_audit_cryptographic_sha256_chaining_and_integrity(tmp_path):
    """Verify continuous SHA-256 hash chaining and mathematical tamper detection."""
    audit_file = tmp_path / "audit_chain_test.jsonl"
    logger = AuditLogger(log_path=audit_file)

    # 1. Write sequence of 3 events
    for i in range(3):
        logger.record_event(
            event_type="REMEDIATION",
            device_host=f"10.0.0.{i + 1}",
            action=f"action_{i}",
            commands=[f"command_{i}"],
            approved=True,
        )

    # 2. Verify clean log passes integrity check
    is_valid, record_count, error = verify_audit_integrity(log_path=audit_file)
    assert is_valid is True
    assert record_count == 3
    assert error is None

    # Inspect records to confirm hash presence
    with open(audit_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line_text) for line_text in f if line_text.strip()]

    assert lines[0]["prev_hash"].startswith("GENESIS_")
    assert lines[1]["prev_hash"] == lines[0]["event_hash"]
    assert lines[2]["prev_hash"] == lines[1]["event_hash"]

    # 3. Tamper with record 2 to confirm mathematical detection
    with open(audit_file, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    tampered_rec = json.loads(raw_lines[1])
    tampered_rec["action"] = "MALICIOUS_TAMPERED_ACTION"
    raw_lines[1] = json.dumps(tampered_rec) + "\n"

    with open(audit_file, "w", encoding="utf-8") as f:
        f.writelines(raw_lines)

    # 4. Verification must detect the tampering
    tampered_valid, tampered_line, tamper_err = verify_audit_integrity(log_path=audit_file)
    assert tampered_valid is False
    assert tampered_line == 2
    assert "Hash mismatch" in tamper_err


# ==============================================================================
# VULN-08: Safe Installer Scripts without Pipe-to-Shell
# ==============================================================================
def test_vuln_08_installer_scripts_do_not_use_pipe_to_shell():
    """Verify that install.ps1 and install.sh do not contain insecure pipe-to-shell invocations."""
    ps1_content = Path("install.ps1").read_text(encoding="utf-8")
    sh_content = Path("install.sh").read_text(encoding="utf-8")

    # install.ps1 must not pipe directly into iex
    assert "irm https://astral.sh/uv/install.ps1 | iex" not in ps1_content
    assert "irm" not in ps1_content or "| iex" not in ps1_content

    # install.sh must not pipe curl into sh
    assert "curl -LsSf https://astral.sh/uv/install.sh | sh" not in sh_content
