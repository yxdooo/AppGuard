"""
ui/notes_dialog.py — Şifreli Not Defteri
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from ui.theme import get_style
from core.backup import _get_key
from core.config import CONFIG_DIR
import os
from cryptography.fernet import Fernet

class NotesDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.notes_file = os.path.join(CONFIG_DIR, "notes.enc")
        
        self.setWindowTitle("🛡️ Şifreli Not Defteri")
        self.setFixedSize(500, 400)
        self.setStyleSheet(get_style("#0f0f23"))
        
        self._build_ui()
        self._load_notes()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        
        lbl = QLabel("Gizli Notlarınız (AES-256 ile şifrelenir)")
        lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        lay.addWidget(lbl)
        
        self.editor = QTextEdit()
        self.editor.setStyleSheet("background: #1a1a2e; color: #f1f5f9; border: 1px solid #2d2d50; border-radius: 6px; padding: 10px;")
        lay.addWidget(self.editor)
        
        btn_row = QHBoxLayout()
        close = QPushButton("Kapat")
        close.setProperty("role", "secondary")
        close.clicked.connect(self.reject)
        btn_row.addWidget(close)
        
        save = QPushButton("Kaydet")
        save.clicked.connect(self._save_notes)
        btn_row.addWidget(save)
        
        lay.addLayout(btn_row)

    def _get_fernet(self) -> Fernet:
        mp = self.config.data.get("master_password")
        # For security, we use the master password's hash to encrypt notes
        if not mp:
            raise Exception("Master password not set")
        salt = bytes.fromhex(mp["salt"]) if isinstance(mp["salt"], str) else mp["salt"].encode()
        key = _get_key(mp["hash"], salt[:16].ljust(16, b'0'))
        return Fernet(key)

    def _load_notes(self):
        if not os.path.exists(self.notes_file):
            return
        try:
            f = self._get_fernet()
            with open(self.notes_file, "rb") as file:
                decrypted = f.decrypt(file.read())
                self.editor.setPlainText(decrypted.decode("utf-8"))
        except Exception:
            pass

    def _save_notes(self):
        try:
            f = self._get_fernet()
            text = self.editor.toPlainText().encode("utf-8")
            encrypted = f.encrypt(text)
            with open(self.notes_file, "wb") as file:
                file.write(encrypted)
            QMessageBox.information(self, "Başarılı", "Notlarınız güvenle şifrelenip kaydedildi.")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Notlar kaydedilemedi: {e}")
