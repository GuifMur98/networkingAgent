"""SQLite Database Manager for persistent, encrypted settings and device inventory."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import SecretStr

from networking_agent.core.crypto import secure_file_permissions, vault
from networking_agent.models.device import DeviceInventory

DB_PATH = Path("data/networking_agent.db")


class DatabaseManager:
    """Manages SQLite storage for encrypted settings and device profiles."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        # WAL mode & memory optimizations for high throughput and safety
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables for settings and device inventory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    is_secret INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    host TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    port INTEGER DEFAULT 22,
                    username TEXT DEFAULT 'admin',
                    password_encrypted TEXT,
                    secret_encrypted TEXT,
                    key_file TEXT,
                    use_keys INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_used_at TEXT
                )
            """)
            conn.commit()
        secure_file_permissions(self.db_path)

    # =========================================================================
    # SETTINGS API (API Keys, Defaults, URLs)
    # =========================================================================
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves and decrypts a setting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value, is_secret FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return default
            val, is_secret = row["value"], bool(row["is_secret"])
            if is_secret and val:
                return vault.decrypt(val)
            return val

    def set_setting(self, key: str, value: str, is_secret: bool = False) -> None:
        """Stores a setting, encrypting it if marked as secret."""
        now = datetime.now(timezone.utc).isoformat()
        stored_val = vault.encrypt(value) if is_secret else value
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO settings (key, value, is_secret, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    is_secret = excluded.is_secret,
                    updated_at = excluded.updated_at
                """,
                (key, stored_val, 1 if is_secret else 0, now),
            )
            conn.commit()

    # =========================================================================
    # DEVICE INVENTORY API
    # =========================================================================
    def list_devices(self) -> List[Dict[str, Any]]:
        """Returns all saved network devices."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices ORDER BY last_used_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def list_device_inventories(self) -> List[DeviceInventory]:
        """Returns all saved network devices as fully hydrated DeviceInventory models."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM devices ORDER BY last_used_at DESC")
            rows = cursor.fetchall()
            devices = []
            for r in rows:
                dev = self.get_device_by_id(r["id"])
                if dev:
                    devices.append(dev)
            return devices

    def get_device_by_id(self, device_id: int) -> Optional[DeviceInventory]:
        """Retrieves a device by ID and decrypts credentials into a DeviceInventory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Decrypt secrets
            raw_password = vault.decrypt(row["password_encrypted"]) if row["password_encrypted"] else None
            raw_secret = vault.decrypt(row["secret_encrypted"]) if row["secret_encrypted"] else None

            # Update last used timestamp
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE devices SET last_used_at = ? WHERE id = ?", (now, device_id))
            conn.commit()

            return DeviceInventory(
                host=row["host"],
                device_type=row["device_type"],
                username=row["username"],
                password=SecretStr(raw_password) if raw_password else None,
                secret=SecretStr(raw_secret) if raw_secret else None,
                port=row["port"],
                key_file=row["key_file"],
                use_keys=bool(row["use_keys"]),
            )

    def save_device(self, device: DeviceInventory, name: Optional[str] = None) -> int:
        """Encrypts credentials and stores device profile in the database."""
        now = datetime.now(timezone.utc).isoformat()
        device_name = name or f"{device.device_type.upper()}-{device.host}"

        enc_password = vault.encrypt(device.password.get_secret_value()) if device.password else None
        enc_secret = vault.encrypt(device.secret.get_secret_value()) if device.secret else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO devices (
                    name, host, device_type, port, username,
                    password_encrypted, secret_encrypted, key_file,
                    use_keys, created_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_name,
                    device.host,
                    device.device_type,
                    device.port,
                    device.username,
                    enc_password,
                    enc_secret,
                    device.key_file,
                    1 if device.use_keys else 0,
                    now,
                    now,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def delete_device(self, device_id: int) -> bool:
        """Removes a device profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            conn.commit()
            return cursor.rowcount > 0


db = DatabaseManager()
