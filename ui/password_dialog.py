"""
ui/password_dialog.py — Password input dialog (theme + i18n + group + strength + hint)
"""
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QInputDialog, QMessageBox, QWidget,
    QFileIconProvider,
)
from PyQt6.QtCore import Qt, QTimer, QFileInfo, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen

from core.i18n import t
from ui.theme import get_style, get_accent_color
from ui.animations import RippleButton


def _get_exe_icon(exe_path: str, size: int = 32) -> QIcon:
    if exe_path and os.path.exists(exe_path):
        try:
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(exe_path))
            if not icon.isNull():
                return icon
        except Exception:
            pass
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(get_accent_color())))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)
    p.end()
    return QIcon(pm)


def _password_strength(pw: str) -> tuple[int, str]:
    if not pw:
        return 0, ""
    score = 0
    if len(pw) >= 6:  score += 15
    if len(pw) >= 10: score += 15
    if len(pw) >= 14: score += 10
    if any(c.isupper() for c in pw): score += 15
    if any(c.islower() for c in pw): score += 10
    if any(c.isdigit() for c in pw): score += 20
    if any(c in r"!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw): score += 15
    if score < 20:  return score, t("strength_very_weak")
    if score < 40:  return score, t("strength_weak")
    if score < 65:  return score, t("strength_medium")
    if score < 85:  return score, t("strength_good")
    return score, t("strength_strong")


class StrengthBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._value = 0

    def set_value(self, v: int):
        self._value = max(0, min(100, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QBrush(QColor("#1e1e38")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 3, 3)
        if self._value > 0:
            fw = int(w * self._value / 100)
            if self._value < 30:   color = "#ef4444"
            elif self._value < 55: color = "#f97316"
            elif self._value < 80: color = "#3b82f6"
            else:                  color = "#22c55e"
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(0, 0, fw, h, 3, 3)


class PasswordDialog(QDialog):
    def __init__(self, app_id: str, auth_id: str, app_name: str, config,
                 is_master: bool = False, is_group: bool = False,
                 exe_path: str = "", usb_available: bool = False,
                 parent=None):
        super().__init__(parent)
        self.app_id   = app_id
        self.auth_id  = auth_id
        self.app_name = app_name
        self.config   = config
        self.is_master = is_master
        self.is_group  = is_group
        self.exe_path  = exe_path
        self._usb_available = usb_available

        self.setWindowTitle("AppGuard")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(410)
        self.setStyleSheet(get_style("#0f0f23"))
        
        self._build_ui()
        self._update_status()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_status)
        self._timer.start(1000)
        self._center()

    def _center(self):
        from PyQt6.QtGui import QGuiApplication
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geo.center().x() - self.width() // 2,
                  geo.center().y() - self.height() // 2)
                  
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#0f0f23")))
        p.setPen(QPen(QColor(get_accent_color()), 2))
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 12, 12)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 26)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(48, 48)
        if self.is_master:
            pm = QPixmap(48, 48)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QBrush(QColor(get_accent_color())))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(4, 4, 40, 40)
            p.end()
            icon_lbl.setPixmap(pm)
        else:
            icon_lbl.setPixmap(_get_exe_icon(self.exe_path, 48).pixmap(48, 48))
        hdr.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(3)
        name_lbl = QLabel(self.app_name)
        name_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")

        if self.is_master:
            sub_text = t("pw_management_panel")
        elif self.is_group:
            sub_text = f"🗂  {t('pw_group_label', name=self.app_name)}"
        else:
            sub_text = t("pw_protected_by")

        sub_lbl = QLabel(sub_text)
        sub_lbl.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
        col.addWidget(name_lbl)
        col.addWidget(sub_lbl)
        hdr.addLayout(col)
        hdr.addStretch()

        # Hint button
        if not self.is_master and not self.is_group:
            app = self.config.get_protected_apps().get(self.auth_id, {})
            hint = app.get("hint", "")
            if hint:
                hint_btn = QPushButton("💡")
                hint_btn.setProperty("role", "icon")
                hint_btn.setFixedSize(32, 32)
                hint_btn.setToolTip(f"Hint: {hint}")
                hdr.addWidget(hint_btn)

        lock_lbl = QLabel("🔒")
        lock_lbl.setFont(QFont("Segoe UI Emoji", 22))
        lock_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        hdr.addWidget(lock_lbl)
        root.addLayout(hdr)

        sep = QFrame(); sep.setProperty("role", "divider")
        root.addWidget(sep)

        self.status_lbl = QLabel()
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setFont(QFont("Segoe UI", 12))
        self.status_lbl.setMinimumHeight(44)
        self.status_lbl.setStyleSheet("background: transparent;")
        root.addWidget(self.status_lbl)

        pw_row = QHBoxLayout()
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_edit.setPlaceholderText(t("pw_enter_ph"))
        self.pw_edit.setFixedHeight(46)
        self.pw_edit.returnPressed.connect(self._submit)
        pw_row.addWidget(self.pw_edit)

        self.eye_btn = QPushButton("👁")
        self.eye_btn.setProperty("role", "icon")
        self.eye_btn.setFixedSize(46, 46)
        self.eye_btn.setCheckable(True)
        self.eye_btn.toggled.connect(self._toggle_echo)
        pw_row.addWidget(self.eye_btn)
        root.addLayout(pw_row)

        self.usb_btn = RippleButton(f"🔑  {t('pw_usb_reset')}")
        self.usb_btn.setProperty("role", "success")
        self.usb_btn.setFixedHeight(40)
        self.usb_btn.clicked.connect(self._usb_reset)
        self.usb_btn.setVisible(self._usb_available)
        root.addWidget(self.usb_btn)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel = RippleButton(t("pw_btn_cancel"))
        cancel.setProperty("role", "secondary")
        cancel.setFixedHeight(44)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        self.ok_btn = RippleButton(t("pw_btn_login"))
        self.ok_btn.setFixedHeight(44)
        self.ok_btn.clicked.connect(self._submit)
        btn_row.addWidget(self.ok_btn)
        root.addLayout(btn_row)

    def _get_status(self) -> dict:
        if self.is_master:
            return {"locked": False, "reason": None, "remaining_seconds": 0, "attempts": 0}
        if self.is_group:
            return self.config.get_group_lockout_status(self.auth_id)
        return self.config.get_lockout_status(self.auth_id)

    def _update_status(self):
        if self.is_master:
            self.status_lbl.setText(t("pw_enter_master"))
            self.status_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self.pw_edit.setEnabled(True)
            self.ok_btn.setEnabled(True)
            return

        s = self._get_status()
        attempts = s["attempts"]
        left = 10 - attempts

        if s["locked"] and s["reason"] == "usb_only":
            self.status_lbl.setText(f"🔴  {t('pw_usb_only')}")
            self.status_lbl.setStyleSheet("color: #f87171; font-weight: 600; background: transparent;")
            self.pw_edit.setEnabled(False)
            self.ok_btn.setEnabled(False)
        elif s["locked"] and s["reason"] == "timer":
            secs = s["remaining_seconds"]
            m, sec = divmod(secs, 60)
            self.status_lbl.setText(
                f"⏳  {t('pw_timer_locked', attempts=attempts, m=m, s=f'{sec:02d}', left=left)}"
            )
            self.status_lbl.setStyleSheet("color: #fbbf24; font-weight: 600; background: transparent;")
            self.pw_edit.setEnabled(False)
            self.ok_btn.setEnabled(False)
        else:
            self.pw_edit.setEnabled(True)
            self.ok_btn.setEnabled(True)
            if attempts == 0:
                self.status_lbl.setText(t("pw_attempts_0"))
                self.status_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            elif attempts < 3:
                self.status_lbl.setText(f"⚠️  {t('pw_attempts_low', attempts=attempts, left=left)}")
                self.status_lbl.setStyleSheet("color: #fbbf24; background: transparent;")
            else:
                self.status_lbl.setText(f"🔴  {t('pw_attempts_high', attempts=attempts, left=left)}")
                self.status_lbl.setStyleSheet("color: #f87171; font-weight: 600; background: transparent;")

    def set_usb_available(self, v: bool):
        self._usb_available = v
        self.usb_btn.setVisible(v)

    def _toggle_echo(self, checked: bool):
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        self.eye_btn.setText("🙈" if checked else "👁")

    def _submit(self):
        pw = self.pw_edit.text()
        if not pw:
            self.pw_edit.setFocus()
            return

        if self.is_master:
            if self.config.verify_master_password(pw):
                self.config.log_activity("Login Successful", "Logged into Management Panel.")
                self._timer.stop(); self.accept()
            else:
                self.config.log_activity("Incorrect Master Password", "Failed login attempt to Management Panel.")
                self.pw_edit.clear()
                self.status_lbl.setText(f"❌  {t('pw_wrong')}")
                self.status_lbl.setStyleSheet("color: #f87171; font-weight: 700; background: transparent;")
                self.pw_edit.setFocus()
            return

        s = self._get_status()
        if s["locked"]:
            return

        if self.is_group:
            ok = self.config.verify_group_password(self.auth_id, pw)
            if ok:
                self.config.record_group_success(self.auth_id)
                self.config.log_activity("Login Successful", f"Group: {self.app_name}")
                self._timer.stop(); self.accept()
            else:
                self.config.record_group_failed(self.auth_id)
                self.config.log_activity("Incorrect Password", f"Group: {self.app_name}")
                self.pw_edit.clear(); self.pw_edit.setFocus()
                self._update_status()
        else:
            ok = self.config.verify_app_password(self.auth_id, pw)
            if ok:
                self.config.record_success(self.auth_id)
                self.config.log_activity("Login Successful", f"App: {self.app_name}")
                self._timer.stop(); self.accept()
            else:
                self.config.record_failed_attempt(self.auth_id)
                self.config.log_activity("Incorrect Password", f"App: {self.app_name}")
                self.pw_edit.clear(); self.pw_edit.setFocus()
                self._update_status()

    def _usb_reset(self):
        from core.usb_detector import get_removable_drives
        connected = {d["serial"] for d in get_removable_drives()}
        wl = {u["serial"] for u in self.config.get_usb_whitelist()}
        if not (connected & wl):
            QMessageBox.warning(self, t("pw_usb_no_title"), t("pw_usb_not_found"))
            return

        new_pw, ok = QInputDialog.getText(self, t("pw_usb_reset"), t("pw_reset_new"),
                                           QLineEdit.EchoMode.Password)
        if not ok or not new_pw.strip():
            return
        confirm, ok2 = QInputDialog.getText(self, t("confirm_pw_title"), t("pw_reset_confirm"),
                                             QLineEdit.EchoMode.Password)
        if not ok2 or new_pw != confirm:
            QMessageBox.warning(self, t("error_title"), t("pw_reset_no_match"))
            return

        if self.is_master:
            self.config.set_master_password(new_pw)
        elif self.is_group:
            self.config.set_group_password(self.auth_id, new_pw)
        else:
            self.config.set_app_password(self.auth_id, new_pw)

        self.config.log_activity("USB Reset", f"Password reset for {self.app_name}.")
        QMessageBox.information(self, t("success_title"), t("pw_reset_success"))
        self._timer.stop(); self.accept()


class PasswordInputWithStrength(QDialog):
    def __init__(self, title: str, label: str, show_hint: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(360)
        self.setStyleSheet(get_style("#0f0f23"))
        self._pw = ""
        self._hint = ""
        self._show_hint = show_hint
        self._build(label)
        self._center()

    def _center(self):
        from PyQt6.QtGui import QGuiApplication
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geo.center().x() - self.width() // 2,
                  geo.center().y() - self.height() // 2)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#0f0f23")))
        p.setPen(QPen(QColor(get_accent_color()), 2))
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 12, 12)

    def _build(self, label: str):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl)

        pw_row = QHBoxLayout()
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_edit.setFixedHeight(44)
        self.pw_edit.textChanged.connect(self._on_changed)
        self.pw_edit.returnPressed.connect(self._submit)
        pw_row.addWidget(self.pw_edit)

        eye = QPushButton("👁")
        eye.setProperty("role", "icon")
        eye.setFixedSize(44, 44)
        eye.setCheckable(True)
        eye.toggled.connect(lambda c: self.pw_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        pw_row.addWidget(eye)
        lay.addLayout(pw_row)

        self.bar = StrengthBar()
        lay.addWidget(self.bar)

        self.strength_lbl = QLabel("")
        self.strength_lbl.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
        lay.addWidget(self.strength_lbl)

        if self._show_hint:
            self.hint_edit = QLineEdit()
            self.hint_edit.setPlaceholderText("Optional: Password hint")
            self.hint_edit.setFixedHeight(44)
            lay.addWidget(self.hint_edit)

        btn_row = QHBoxLayout()
        cancel = RippleButton(t("pw_btn_cancel"))
        cancel.setProperty("role", "secondary")
        cancel.setFixedHeight(42)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok = RippleButton("Tamam  →")
        ok.setFixedHeight(42)
        ok.clicked.connect(self._submit)
        btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _on_changed(self, text: str):
        score, label = _password_strength(text)
        self.bar.set_value(score)
        self.strength_lbl.setText(label)

    def _submit(self):
        pw = self.pw_edit.text()
        if pw:
            self._pw = pw
            if self._show_hint:
                self._hint = self.hint_edit.text()
            self.accept()

    def get_password(self) -> str:
        return self._pw

    def get_hint(self) -> str:
        return self._hint
