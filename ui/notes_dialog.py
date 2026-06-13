"""
ui/notes_dialog.py — Encrypted Notepad

Notes are encrypted with AES-256-GCM via the shared crypto helpers.
The encryption key is derived from the raw master password using HKDF-SHA256
so that:
  - The Argon2 hash stored on disk is NOT used as key material.
  - The key is cryptographically bound to a fixed "notes" context string,
    preventing ciphertext from being reused for any other purpose.
  - No per-note salt is needed because AES-GCM uses a fresh random nonce
    on every encrypt call.
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton,
    QHBoxLayout, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt

from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

from core.config import CONFIG_DIR
from core.crypto import encrypt_data, decrypt_data
from core.i18n import t
from ui.theme import get_style

# AAD that binds every notes ciphertext to this specific purpose.
_NOTES_AAD = b"appguard-notes-v1"


def _derive_notes_key(master_password: str) -> bytes:
    """
    Derive a 32-byte AES-256 key from *master_password* using HKDF-SHA256.

    A fixed application-specific salt provides additional domain separation
    beyond the info parameter, ensuring this key can never be confused with
    a key derived for a different component of the application.
    The info parameter pins the key to the 'notes' context so that the same
    master password cannot be used to derive keys for other purposes.
    """
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=b"appguard-notes-hkdf-salt-v1",  # fixed application salt
        info=b"appguard-notes-v1",
        backend=default_backend(),
    ).derive(master_password.encode("utf-8"))


class NotesDialog(QDialog):
    """AES-256-GCM encrypted notepad dialog."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.notes_file = os.path.join(CONFIG_DIR, "notes.enc")

        self.setWindowTitle(f"🛡️ {t('tab_notes')}")
        self.setFixedSize(520, 420)
        self.setStyleSheet(get_style("#0f0f23"))

        self._build_ui()
        self._load_notes()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)

        lbl = QLabel("Secret Notes (Encrypted with AES-256-GCM)")
        lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        lay.addWidget(lbl)

        self.editor = QTextEdit()
        self.editor.setStyleSheet(
            "background: #1a1a2e; color: #f1f5f9;"
            " border: 1px solid #2d2d50; border-radius: 6px; padding: 10px;"
        )
        lay.addWidget(self.editor)

        btn_row = QHBoxLayout()

        # Use t() directly; it falls back to the key name if not translated.
        close_btn = QPushButton(t("btn_close"))
        close_btn.setProperty("role", "secondary")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)

        save_btn = QPushButton(t("btn_save"))
        save_btn.clicked.connect(self._save_notes)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _get_key(self) -> bytes:
        """
        Return the AES-256 notes key, derived from the master password.

        Raises RuntimeError if no master password has been set yet.
        The key is derived fresh on every call (cheap HKDF, no disk I/O).
        """
        mp = self.config.data.get("master_password")
        if not mp:
            raise RuntimeError("Master password is not set.")

        # Ask the caller for the raw password at dialog-open time.
        # At this point the user has already authenticated via PasswordDialog,
        # so we can retrieve the password from the session cache if the
        # controller stores it, OR we derive from the hash — but that is
        # insecure.  The cleanest solution: store the verified plaintext
        # password temporarily on the config object during the session.
        raw_pw = getattr(self.config, "_session_master_pw", None)
        if not raw_pw:
            raise RuntimeError(
                "Session master password not available. "
                "Please close and reopen the panel."
            )

        return _derive_notes_key(raw_pw)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load_notes(self) -> None:
        if not os.path.exists(self.notes_file):
            return
        try:
            key = self._get_key()
            with open(self.notes_file, "rb") as fh:
                ciphertext = fh.read()
            plaintext = decrypt_data(ciphertext, key, aad=_NOTES_AAD)
            self.editor.setPlainText(plaintext.decode("utf-8"))
        except RuntimeError as exc:
            # Session key not available — show an informative message.
            QMessageBox.warning(self, "Encrypted Notepad", str(exc))
        except InvalidTag:
            QMessageBox.warning(
                self, "Decryption Failed",
                "Notes could not be decrypted. The file may be corrupt "
                "or the master password has changed.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not load notes: {exc}")

    def _save_notes(self) -> None:
        try:
            key = self._get_key()
            plaintext = self.editor.toPlainText().encode("utf-8")
            ciphertext = encrypt_data(plaintext, key, aad=_NOTES_AAD)

            # Atomic write: temp file → os.replace()
            tmp = self.notes_file + ".tmp"
            try:
                with open(tmp, "wb") as fh:
                    fh.write(ciphertext)
                os.replace(tmp, self.notes_file)
            except Exception:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise

            QMessageBox.information(
                self, "Saved", "Your notes have been securely encrypted and saved."
            )
            self.accept()
        except RuntimeError as exc:
            QMessageBox.warning(self, "Encrypted Notepad", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Notes could not be saved: {exc}")
