"""
ui/setup_dialog.py — Initial setup wizard (language + theme selection)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.i18n import t, set_lang, get_lang
from ui.theme import ACCENT_COLORS, set_accent, get_accent, get_style


_LANG_OPTIONS = [("tr", "Türkçe"), ("en", "English")]
_THEME_KEYS   = list(ACCENT_COLORS.keys())


class SetupDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        # Load saved language/theme if available
        lang = config.get_setting("language", "tr")
        theme = config.get_setting("theme", "purple")
        set_lang(lang)
        set_accent(theme)

        self.setWindowTitle(f"AppGuard — {t('setup_title')}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(440)
        self.setStyleSheet(get_style("#0f0f23"))

        self._build_ui()
        self._center()

    def _center(self):
        from PyQt6.QtGui import QGuiApplication
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geo.center().x() - self.width() // 2,
                  geo.center().y() - self.height() // 2)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(16)

        # Logo
        icon = QLabel("🛡️")
        icon.setFont(QFont("Segoe UI Emoji", 40))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background: transparent;")
        lay.addWidget(icon)

        # Title
        self.title_lbl = QLabel(t("setup_welcome"))
        self.title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(t("setup_desc"))
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: #64748b; font-size: 12px; background: transparent;")
        self.desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.desc_lbl)

        # Separator
        sep = QFrame(); sep.setProperty("role", "divider")
        lay.addWidget(sep)

        # ── Language + Theme ──
        opts_row = QHBoxLayout()
        opts_row.setSpacing(12)

        lang_col = QVBoxLayout()
        self.lang_lbl = QLabel(t("setup_language_label"))
        self.lang_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; background: transparent;")
        lang_col.addWidget(self.lang_lbl)
        self.lang_cb = QComboBox()
        for code, name in _LANG_OPTIONS:
            self.lang_cb.addItem(name, code)
            if code == get_lang():
                self.lang_cb.setCurrentIndex(self.lang_cb.count() - 1)
        self.lang_cb.currentIndexChanged.connect(self._on_lang_change)
        lang_col.addWidget(self.lang_cb)
        opts_row.addLayout(lang_col)

        theme_col = QVBoxLayout()
        self.theme_lbl = QLabel(t("setup_theme_label"))
        self.theme_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; background: transparent;")
        theme_col.addWidget(self.theme_lbl)
        self.theme_cb = QComboBox()
        for key in _THEME_KEYS:
            self.theme_cb.addItem(t(f"theme_{key}"), key)
            if key == get_accent():
                self.theme_cb.setCurrentIndex(self.theme_cb.count() - 1)
        self.theme_cb.currentIndexChanged.connect(self._on_theme_change)
        theme_col.addWidget(self.theme_cb)
        opts_row.addLayout(theme_col)

        lay.addLayout(opts_row)

        sep2 = QFrame(); sep2.setProperty("role", "divider")
        lay.addWidget(sep2)

        # ── Passwords ──
        self.pw1_lbl = QLabel(t("setup_master_pw"))
        self.pw1_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600; background: transparent;")
        lay.addWidget(self.pw1_lbl)

        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw1.setPlaceholderText(t("setup_ph_master"))
        self.pw1.setFixedHeight(46)
        lay.addWidget(self.pw1)

        # Password strength bar
        from ui.password_dialog import StrengthBar, _password_strength
        self.strength_bar = StrengthBar()
        lay.addWidget(self.strength_bar)

        self.strength_lbl = QLabel("")
        self.strength_lbl.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
        lay.addWidget(self.strength_lbl)

        self.pw1.textChanged.connect(self._on_pw_changed)

        self.pw2_lbl = QLabel(t("setup_confirm_pw"))
        self.pw2_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600; background: transparent;")
        lay.addWidget(self.pw2_lbl)

        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw2.setPlaceholderText(t("setup_ph_confirm"))
        self.pw2.setFixedHeight(46)
        self.pw2.returnPressed.connect(self._submit)
        lay.addWidget(self.pw2)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet("color: #f87171; font-size: 12px; background: transparent;")
        self.err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.err_lbl)

        self.ok_btn = QPushButton(t("setup_btn_complete"))
        self.ok_btn.setFixedHeight(48)
        self.ok_btn.clicked.connect(self._submit)
        lay.addWidget(self.ok_btn)

    def _on_pw_changed(self, text: str):
        from ui.password_dialog import StrengthBar, _password_strength
        score, lbl = _password_strength(text)
        self.strength_bar.set_value(score)
        self.strength_lbl.setText(lbl)

    def _on_lang_change(self):
        lang = self.lang_cb.currentData()
        set_lang(lang)
        self.config.set_setting("language", lang)
        self._refresh_texts()

    def _on_theme_change(self):
        theme = self.theme_cb.currentData()
        set_accent(theme)
        self.config.set_setting("theme", theme)
        self.setStyleSheet(get_style("#0f0f23"))

    def _refresh_texts(self):
        """Update all texts when language changes."""
        self.setWindowTitle(f"AppGuard — {t('setup_title')}")
        self.title_lbl.setText(t("setup_welcome"))
        self.desc_lbl.setText(t("setup_desc"))
        self.lang_lbl.setText(t("setup_language_label"))
        self.theme_lbl.setText(t("setup_theme_label"))
        self.pw1_lbl.setText(t("setup_master_pw"))
        self.pw1.setPlaceholderText(t("setup_ph_master"))
        self.pw2_lbl.setText(t("setup_confirm_pw"))
        self.pw2.setPlaceholderText(t("setup_ph_confirm"))
        self.ok_btn.setText(t("setup_btn_complete"))
        
        for i, key in enumerate(_THEME_KEYS):
            self.theme_cb.setItemText(i, t(f"theme_{key}"))

    def _submit(self) -> None:
        p1, p2 = self.pw1.text(), self.pw2.text()
        if len(p1) < 8:
            self.err_lbl.setText(f"❌  {t('setup_err_min')}")
            return
        if p1 != p2:
            self.err_lbl.setText(f"❌  {t('setup_err_match')}")
            self.pw2.clear(); self.pw2.setFocus()
            return
        self.config.set_master_password(p1)
        self.accept()
