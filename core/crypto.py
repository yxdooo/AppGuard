"""
core/crypto.py — Encryption, Hashing and Security (Argon2id + AES-256-GCM + DPAPI)
"""
import os
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

try:
    import win32crypt
    _DPAPI_AVAILABLE = True
except ImportError:
    _DPAPI_AVAILABLE = False

ph = PasswordHasher()

# Context string bound to every AES-GCM ciphertext as Additional Authenticated
# Data (AAD). Prevents a valid ciphertext produced for one context from being
# replayed in a different context (confused-deputy / splice attack).
_AAD = b"appguard-config-v1"



# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash *password* with Argon2id and return the encoded hash string.

    The Argon2 library generates its own random salt internally; callers must
    NOT pass an external salt.
    """
    return ph.hash(password)


def verify_password(
    password: str,
    stored_hash: str,
    legacy_salt: str | None = None,
) -> tuple[bool, bool]:
    """
    Verify *password* against *stored_hash*.

    Returns
    -------
    (verified, needs_rehash) : tuple[bool, bool]
        ``verified``     – True if the password is correct.
        ``needs_rehash`` – True when the hash is a legacy SHA-256 hash and
                           the caller should upgrade it to Argon2id now that
                           the plaintext password is available.

    Supports:
    * Argon2id hashes (current scheme, ``$argon2*`` prefix).
    * Legacy SHA-256 hashes (migration path; requires *legacy_salt*).
    """
    if stored_hash.startswith("$argon2"):
        try:
            ph.verify(stored_hash, password)
            # Also rehash if the Argon2 parameters (memory, iterations, etc.)
            # have been updated since this hash was generated.
            upgrade = ph.check_needs_rehash(stored_hash)
            return True, upgrade
        except VerifyMismatchError:
            return False, False

    if legacy_salt:
        combined = (password + legacy_salt).encode("utf-8")
        if hashlib.sha256(combined).hexdigest() == stored_hash:
            # Password is correct but stored as weak SHA-256 — caller should
            # re-hash with Argon2id and persist the new hash.
            return True, True

    return False, False


# ---------------------------------------------------------------------------
# Machine key (DPAPI)
# ---------------------------------------------------------------------------

def get_machine_key(key_path: str) -> bytes:
    """
    Return the 32-byte AES-256 machine key, persisted via Windows DPAPI.

    * If the key file exists and DPAPI can decrypt it successfully, the key is
      returned as-is.  The file is **never** silently overwritten.
    * If the key file is absent, a new random key is generated, DPAPI-encrypted,
      and saved.
    * If DPAPI decryption fails (corrupted file, user migration, etc.) a
      ``RuntimeError`` is raised so the caller can present a meaningful error
      to the user rather than silently destroying all previously encrypted data.

    Raises
    ------
    RuntimeError
        When DPAPI is not available (non-Windows platform) or when an existing
        key file cannot be decrypted.
    """
    if not _DPAPI_AVAILABLE:
        raise RuntimeError(
            "Windows DPAPI is not available on this platform. "
            "AppGuard currently requires Windows."
        )

    entropy = b"AppGuard-Config-Key"

    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            enc_key = f.read()
        try:
            _, key = win32crypt.CryptUnprotectData(enc_key, entropy, None, None, 0)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to decrypt the AppGuard machine key at '{key_path}'. "
                "The key file may be corrupted or belong to a different Windows "
                f"user account. Original error: {exc}"
            ) from exc

        if len(key) != 32:
            raise RuntimeError(
                f"Decrypted machine key has unexpected length {len(key)} "
                "(expected 32 bytes). The key file may be corrupted."
            )
        return key

    # No key file yet — generate and persist a fresh one.
    key = os.urandom(32)
    enc_key = win32crypt.CryptProtectData(key, "AppGuard Config Key", entropy, None, None, 0)

    # Write to a temp file first, then atomically replace the target so that a
    # mid-write crash cannot leave a truncated / corrupt key file behind.
    tmp_path = key_path + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(enc_key)
        os.replace(tmp_path, key_path)  # atomic on same filesystem (POSIX + Windows)
    except Exception:
        # Clean up orphaned temp file if the replace itself failed.
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    # Mark file as hidden so it does not clutter the config directory.
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(key_path, 2)  # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass  # Non-fatal; hiding the file is cosmetic only.

    return key


# ---------------------------------------------------------------------------
# Symmetric encryption (AES-256-GCM)
# ---------------------------------------------------------------------------

def encrypt_data(data: bytes, key: bytes, aad: bytes = _AAD) -> bytes:
    """
    Encrypt *data* with AES-256-GCM.

    The 12-byte random nonce is prepended to the returned ciphertext so that
    ``decrypt_data`` can extract it without an out-of-band channel.

    *aad* (Additional Authenticated Data) is bound to the ciphertext via the
    GCM authentication tag.  Any attempt to decrypt the blob with a different
    *aad* value will fail with an ``InvalidTag`` exception, preventing
    ciphertext from being replayed in a different context.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, data, aad)


def decrypt_data(encrypted_data: bytes, key: bytes, aad: bytes = _AAD) -> bytes:
    """
    Decrypt *encrypted_data* produced by :func:`encrypt_data`.

    Raises ``cryptography.exceptions.InvalidTag`` if the key, nonce, AAD, or
    ciphertext has been tampered with.
    """
    aesgcm = AESGCM(key)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    return aesgcm.decrypt(nonce, ciphertext, aad)
