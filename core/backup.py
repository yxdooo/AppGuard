"""
core/backup.py — Şifreli yedekleme sistemi (.agbackup)
Ayarları, profilleri ve uygulamaları AES-256-GCM ile şifreler/çözer.
"""
import json
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from core.crypto import encrypt_data, decrypt_data


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
        
        # File format: salt (16 bytes) + encrypted data
        with open(filepath, 'wb') as file:
            file.write(salt + encrypted)
        return True
    except Exception as e:
        print(f"Backup error: {e}")
        return False


def restore_backup(password: str, filepath: str) -> dict | None:
    try:
        with open(filepath, 'rb') as file:
            content = file.read()
            
        salt = content[:16]
        encrypted = content[16:]
        
        key = _get_key(password, salt)
        
        # Try to decrypt using AES-GCM
        try:
            decrypted = decrypt_data(encrypted, key)
            return json.loads(decrypted.decode('utf-8'))
        except Exception:
            # Fallback to legacy Fernet (AES-128-CBC)
            import base64
            from cryptography.fernet import Fernet
            
            legacy_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            legacy_key = base64.urlsafe_b64encode(legacy_kdf.derive(password.encode()))
            f = Fernet(legacy_key)
            decrypted = f.decrypt(encrypted)
            return json.loads(decrypted.decode('utf-8'))
            
    except Exception as e:
        print(f"Restore error: {e}")
        return None
