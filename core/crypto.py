"""
core/crypto.py — Encryption, Hashing and Security (Argon2id + AES-256-GCM + DPAPI)
"""
import os
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import win32crypt

ph = PasswordHasher()

def generate_salt() -> str:
    """For legacy compatibility (used in the old SHA-256 system)."""
    return secrets.token_hex(32)

def hash_password(password: str, legacy_salt: str = None) -> str:
    """
    Hashes password with Argon2id. (legacy_salt for signature compat only)
    """
    return ph.hash(password)

def verify_password(password: str, stored_hash: str, legacy_salt: str = None) -> bool:
    """
    Verifies password. Supports both Argon2 and legacy SHA-256 (migration).
    """
    if stored_hash.startswith("$argon2"):
        try:
            return ph.verify(stored_hash, password)
        except VerifyMismatchError:
            return False
    elif legacy_salt:
        # Legacy SHA-256 check
        combined = (password + legacy_salt).encode("utf-8")
        if hashlib.sha256(combined).hexdigest() == stored_hash:
            # Note: Automatic migration to Argon2 can be done in config.py.
            return True
    return False

def get_machine_key(key_path: str) -> bytes:
    """
    Fetches machine-specific AES-256 key using Windows DPAPI.
    Creates if missing and saves encrypted. Used for config encryption.
    """
    entropy = b"AppGuard-Config-Key"
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            enc_key = f.read()
        try:
            _, key = win32crypt.CryptUnprotectData(enc_key, entropy, None, None, 0)
            if len(key) == 32:
                return key
        except Exception:
            pass

    # Generate new key
    key = os.urandom(32)
    enc_key = win32crypt.CryptProtectData(key, "AppGuard Config Key", entropy, None, None, 0)
    
    # Remove hidden attribute if file exists and is hidden to be able to write
    if os.path.exists(key_path):
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(key_path, 128) # FILE_ATTRIBUTE_NORMAL
        except Exception:
            pass

    with open(key_path, "wb") as f:
        f.write(enc_key)
        
    # Make file hidden
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(key_path, 2) # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass
    return key

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """Encrypts data using AES-256-GCM."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, data, None)

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypts data using AES-256-GCM."""
    aesgcm = AESGCM(key)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)
