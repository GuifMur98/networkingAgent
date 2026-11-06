"""Unit tests for SQLite database manager."""

from pydantic import SecretStr

from networking_agent.core.crypto import SecretVault
from networking_agent.core.db import DatabaseManager
from networking_agent.models.device import DeviceInventory


def test_sqlite_settings_storage(tmp_path, monkeypatch):
    key_file = tmp_path / "test.key"
    test_vault = SecretVault(key_path=key_file)
    monkeypatch.setattr("networking_agent.core.db.vault", test_vault)

    db_file = tmp_path / "test.db"
    manager = DatabaseManager(db_path=db_file)

    # Save and retrieve regular setting
    manager.set_setting("ai_provider", "gemini", is_secret=False)
    assert manager.get_setting("ai_provider") == "gemini"

    # Save and retrieve encrypted secret setting
    manager.set_setting("gemini_api_key", "secret_gemini_key_abc", is_secret=True)
    decrypted_key = manager.get_setting("gemini_api_key")
    assert decrypted_key == "secret_gemini_key_abc"


def test_sqlite_device_inventory_storage(tmp_path, monkeypatch):
    key_file = tmp_path / "test.key"
    test_vault = SecretVault(key_path=key_file)
    monkeypatch.setattr("networking_agent.core.db.vault", test_vault)

    db_file = tmp_path / "test.db"
    manager = DatabaseManager(db_path=db_file)

    device = DeviceInventory(
        host="192.168.88.1",
        device_type="mikrotik_routeros",
        username="admin",
        password=SecretStr("mikrotik_pass_999"),
    )

    dev_id = manager.save_device(device, name="MikroTik Core Router")
    assert dev_id > 0

    saved_list = manager.list_devices()
    assert len(saved_list) == 1
    assert saved_list[0]["name"] == "MikroTik Core Router"
    assert saved_list[0]["host"] == "192.168.88.1"

    # Retrieve device with decrypted password
    retrieved = manager.get_device_by_id(dev_id)
    assert retrieved is not None
    assert retrieved.host == "192.168.88.1"
    assert retrieved.device_type == "mikrotik_routeros"
    assert retrieved.password.get_secret_value() == "mikrotik_pass_999"

    # Delete device
    assert manager.delete_device(dev_id) is True
    assert len(manager.list_devices()) == 0
