"""Cryptographic encryption and decryption for sensitive credentials and API keys."""

import os
import stat
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

from networking_agent.core.logging import logger

KEY_PATH = Path("data/.vault.key")


def secure_file_permissions(path: Path) -> None:
    """Restricts file permissions to owner read/write (0600) on platforms supporting it."""
    try:
        if path.exists():
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


class SecretVault:
    """Provides local symmetric encryption for database credentials and API keys."""

    def __init__(self, key_path: Optional[Path] = None):
        self.key_path = key_path or KEY_PATH
        self._fernet: Optional[Fernet] = None

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.key_path.exists():
                logger.debug(f"Generating new cryptographic master key at {self.key_path}...")
                key = Fernet.generate_key()
                with open(self.key_path, "wb") as f:
                    f.write(key)
                secure_file_permissions(self.key_path)
            else:
                with open(self.key_path, "rb") as f:
                    key = f.read().strip()
                secure_file_permissions(self.key_path)
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """Encrypts plaintext string into an encrypted Fernet token string."""
        if plaintext is None:
            return None
        if not plaintext:
            return ""
        fernet = self._get_fernet()
        token = fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """Decrypts a Fernet token string back into the original plaintext."""
        if ciphertext is None:
            return None
        if not ciphertext:
            return ""
        try:
            fernet = self._get_fernet()
            decrypted = fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"[bold red]Decryption failed:[/bold red] {e}")
            return None


vault = SecretVault()
