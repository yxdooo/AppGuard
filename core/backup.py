"""
core/backup.py — Encrypted backup system (.agbackup)
Encrypts/decrypts settings, profiles and apps with AES-256-GCM.
"""
import json
import logging
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from core.crypto import encrypt_data, decrypt_data

log = logging.getLogger(__name__)


def _get_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256-bit key for AES-256-GCM
        salt=salt,
        iterations=200000,
    )
    return kdf.derive(password.encode())


def create_backup(data: dict, password: str, filepath: str) -> bool:
    try:
        salt = os.urandom(16)
        key = _get_key(password, salt)
        
        raw_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        encrypted = encrypt_data(raw_data, key)
        
        # Atomic write: salt (16 bytes) + encrypted data
        tmp = filepath + ".tmp"
        try:
            with open(tmp, 'wb') as file:
                file.write(salt + encrypted)
            os.replace(tmp, filepath)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        return True
    except Exception as e:
        log.error("Backup error: %s", e, exc_info=True)
        return False


def restore_backup(password: str, filepath: str) -> dict | None:
    try:
        with open(filepath, "rb") as file:
            content = file.read()

        # Minimum valid file: 16-byte salt + 28-byte AES-GCM blob = 44 bytes.
        if len(content) < 44:
            raise ValueError(
                f"Backup file is too short ({len(content)} bytes); it may be corrupted."
            )

        salt      = content[:16]
        encrypted = content[16:]
        
        key = _get_key(password, salt)
        
        try:
            decrypted = decrypt_data(encrypted, key)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            # Fallback: try legacy Fernet (AES-128-CBC, 100k PBKDF2 iterations).
            # WARNING: 100k PBKDF2-SHA256 iterations is below the 2023 NIST
            # recommendation of 600k. Legacy backups are weaker; prompt the
            # user to re-export after a successful restore.
            import base64
            from cryptography.fernet import Fernet

            legacy_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100_000,
            )
            legacy_key = base64.urlsafe_b64encode(legacy_kdf.derive(password.encode()))
            f = Fernet(legacy_key)
            decrypted = f.decrypt(encrypted)
            log.warning(
                "Restored from a legacy backup (weak 100k-iteration PBKDF2). "
                "Please re-export a new backup to use the current encryption."
            )
            return json.loads(decrypted.decode("utf-8"))

    except Exception as e:
        log.error("Restore error: %s", e, exc_info=True)
        return None
