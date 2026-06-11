import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, SwitchSettingCard, FluentIcon as FIF,
    Action, RoundMenu, PrimaryPushButton, SettingCard, ComboBox,
    SettingCardGroup, PushSettingCard
)
from core.backup import create_backup, restore_backup
from ui.password_dialog import PasswordInputWithStrength
from core.i18n import t

class SimpleComboBoxSettingCard(SettingCard):
    def __init__(self, icon, title, content=None, texts=[], parent=None):
        super().__init__(icon, title, content, parent)
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(texts)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

class SettingsInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.main_window = main_window
        self.config = main_window.config
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("ScrollArea {background: transparent; border: none}")
        self.view.setStyleSheet("QWidget {background: transparent}")
        
        self.vBoxLayout.setContentsMargins(36, 36, 36, 36)
        self.vBoxLayout.setSpacing(16)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.titleLabel = SubtitleLabel(t("tab_settings"), self.view)
        self.vBoxLayout.addWidget(self.titleLabel)
        
        # Security Group
        self.securityGroup = SettingCardGroup(t("general_section"), self.view)
        
        self.guardianCard = SwitchSettingCard(
            FIF.APPLICATION,
            t("setting_guardian"),
            t("guardian_desc"),
            configItem=None,
            parent=self.securityGroup
        )
        self.guardianCard.checkedChanged.connect(self._toggle_guardian)
        self.securityGroup.addSettingCard(self.guardianCard)
        
        self.remoteLockCard = SwitchSettingCard(
            FIF.PHONE,
            t("remote_section"),
            t("remote_desc"),
            configItem=None,
            parent=self.securityGroup
        )
        self.remoteLockCard.checkedChanged.connect(self._toggle_remote_lock)
        self.securityGroup.addSettingCard(self.remoteLockCard)
        
        self.qrBtnCard = PushSettingCard(
            t("btn_show"),
            FIF.QRCODE,
            t("btn_qr"),
            t("qr_desc"),
            self.securityGroup
        )
        self.qrBtnCard.clicked.connect(self._show_qr)
        self.securityGroup.addSettingCard(self.qrBtnCard)

        self.stealthCard = SwitchSettingCard(
            FIF.HIDE,
            t("stealth_mode"),
            t("stealth_desc"),
            configItem=None,
            parent=self.securityGroup
        )
        self.stealthCard.checkedChanged.connect(self._toggle_stealth)
        self.securityGroup.addSettingCard(self.stealthCard)

        self.stealthHotkeyCard = PushSettingCard(
            t("setting_hotkey_btn"),
            FIF.COMMAND_PROMPT,
            t("stealth_hotkey"),
            "Ctrl+Shift+H",
            self.securityGroup
        )
        self.stealthHotkeyCard.clicked.connect(self._change_stealth_hotkey)
        self.securityGroup.addSettingCard(self.stealthHotkeyCard)

        self.vBoxLayout.addWidget(self.securityGroup)

        # Appearance / Language Group
        self.appearanceGroup = SettingCardGroup(t("appearance_section"), self.view)
        
        self.languageCard = SimpleComboBoxSettingCard(
            FIF.LANGUAGE,
            t("setting_language"),
            "Change to English or Turkish (Restart app to apply)",
            texts=["Türkçe", "English"],
            parent=self.appearanceGroup
        )
        self.languageCard.comboBox.setCurrentIndex(0 if self.config.get_setting("language", "tr") == "tr" else 1)
        self.languageCard.comboBox.currentIndexChanged.connect(self._change_language)
        self.appearanceGroup.addSettingCard(self.languageCard)
        
        self.vBoxLayout.addWidget(self.appearanceGroup)

        # System Group
        self.sysGroup = SettingCardGroup(t("system_section"), self.view)
        self.startupCard = SwitchSettingCard(
            FIF.POWER_BUTTON,
            t("setting_startup"),
            t("startup_desc"),
            configItem=None,
            parent=self.sysGroup
        )
        self.startupCard.checkedChanged.connect(self._toggle_startup)
        self.sysGroup.addSettingCard(self.startupCard)
        self.vBoxLayout.addWidget(self.sysGroup)

        # Backup Group
        self.backupGroup = SettingCardGroup(t("backup_section"), self.view)
        self.backupBtn = PushSettingCard(t("file_export"), FIF.DOWNLOAD, t("btn_backup"), t("backup_desc"), self.backupGroup)
        self.backupBtn.clicked.connect(self._backup)
        self.backupGroup.addSettingCard(self.backupBtn)
        
        self.restoreBtn = PushSettingCard(t("file_import"), FIF.FOLDER, t("btn_restore"), t("restore_desc"), self.backupGroup)
        self.restoreBtn.clicked.connect(self._restore)
        self.backupGroup.addSettingCard(self.restoreBtn)
        self.vBoxLayout.addWidget(self.backupGroup)
        
        self._sync_ui()

    def _sync_ui(self):
        self.startupCard.setChecked(self.config.get_setting("start_with_windows", False))
        self.guardianCard.setChecked(self.config.get_setting("guardian_enabled", False))
        self.remoteLockCard.setChecked(self.config.get_setting("remote_lock_enabled", False))
        self.stealthCard.setChecked(self.config.get_setting("stealth_mode_enabled", False))
        self.stealthHotkeyCard.setContent(self.config.get_setting("stealth_hotkey", "ctrl+shift+h"))

    def _toggle_stealth(self, state):
        self.config.set_setting("stealth_mode_enabled", bool(state))
        if hasattr(self.main_window, "_update_stealth_mode"):
            self.main_window._update_stealth_mode()
            
    def _change_stealth_hotkey(self):
        from PyQt6.QtWidgets import QInputDialog
        new_hk, ok = QInputDialog.getText(self, t("stealth_hotkey"), t("setting_hotkey_prompt"))
        if ok and new_hk.strip():
            self.config.set_setting("stealth_hotkey", new_hk.strip().lower())
            self.stealthHotkeyCard.setContent(new_hk.strip().lower())
            QMessageBox.information(self, t("success_title"), t("setting_hotkey_updated"))
            if hasattr(self.main_window, "_rebind_hotkeys"):
                self.main_window._rebind_hotkeys()

    def _change_language(self, index):
        lang = "tr" if index == 0 else "en"
        self.config.set_setting("language", lang)
        QMessageBox.information(self, t("success_title"), "Language changed. Please restart the app.")
        
    def _toggle_guardian(self, state):
        self.config.set_setting("guardian_enabled", bool(state))

    def _toggle_remote_lock(self, state):
        self.config.set_setting("remote_lock_enabled", bool(state))
        if state and self.main_window.remote_server is None:
            self.main_window._restart_remote_server()
            
    def _show_qr(self):
        from core.remote_lock import get_local_ip, generate_qr_code
        from PyQt6.QtWidgets import QDialog, QLabel
        from PyQt6.QtGui import QPixmap
        
        ip = get_local_ip()
        token = self.config.get_setting("remote_lock_token")
        if not token:
            import secrets
            token = secrets.token_urlsafe(16)
            self.config.set_setting("remote_lock_token", token)
            
        generate_qr_code(ip, 8080, token, self.main_window.qr_path)
        
        dlg = QDialog(self)
        dlg.setWindowTitle(t("scan_phone"))
        lay = QVBoxLayout(dlg)
        lbl = QLabel()
        lbl.setPixmap(QPixmap(self.main_window.qr_path))
        lay.addWidget(lbl)
        
        info = QLabel(f"{t('same_network')}\n{ip}:8080")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)
        dlg.exec()

    def _toggle_startup(self, state):
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AppGuard"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if state:
                import sys
                exe = sys.executable.replace("python.exe", "pythonw.exe")
                script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "main.py")
                script = os.path.normpath(script)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe}" "{script}"')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.config.set_setting("start_with_windows", bool(state))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Startup setting could not be changed: {e}")

    def _backup(self):
        dlg = PasswordInputWithStrength(t("backup_section"), "Backup File Password (New):", parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted: return
        pw = dlg.get_password()
        
        path, _ = QFileDialog.getSaveFileName(self, "Save", "appguard_backup.agbackup", "Backup (*.agbackup)")
        if path:
            if create_backup(self.config.data, pw, path):
                QMessageBox.information(self, t("success_title"), "Backup created.")
            else:
                QMessageBox.warning(self, t("error_title"), "Backup failed.")

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "Backup (*.agbackup)")
        if not path: return
        
        dlg = PasswordInputWithStrength(t("backup_section"), "Backup Password:", parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted: return
        pw = dlg.get_password()
        
        data = restore_backup(pw, path)
        if data:
            self.config.data = data
            self.config.save()
            QMessageBox.information(self, t("success_title"), "Restored. Please restart the application.")
            self.main_window.close()
        else:
            QMessageBox.warning(self, t("error_title"), "Wrong password or corrupted file.")
