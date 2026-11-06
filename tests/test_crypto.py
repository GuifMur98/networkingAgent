"""Unit tests for cryptographic vault encryption and decryption."""

from networking_agent.core.crypto import SecretVault


def test_vault_encryption_decryption_cycle(tmp_path):
    key_file = tmp_path / "test.key"
    vault = SecretVault(key_path=key_file)

    secret_text = "super_secret_ssh_password_123"
    encrypted = vault.encrypt(secret_text)
    assert encrypted != secret_text
    assert isinstance(encrypted, str)

    decrypted = vault.decrypt(encrypted)
    assert decrypted == secret_text


def test_vault_handles_empty_and_none(tmp_path):
    key_file = tmp_path / "test.key"
    vault = SecretVault(key_path=key_file)

    assert vault.encrypt(None) is None
    assert vault.decrypt(None) is None
    assert vault.encrypt("") == ""
    assert vault.decrypt("") == ""
