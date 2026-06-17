import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, Theme, 
    FluentIcon as FIF, SplashScreen
)

from ui.pages.dashboard import DashboardInterface
from ui.pages.apps_interface import AppLockInterface
from ui.pages.groups_interface import GroupsInterface
from ui.pages.usb_interface import UsbInterface
from ui.pages.settings_interface import SettingsInterface
from core.config import CONFIG_DIR
from ui.password_dialog import PasswordInputWithStrength
from PyQt6.QtWidgets import QMessageBox
from core.i18n import t

class MainWindow(FluentWindow):
    def __init__(self, config, controller=None, emergency_lock_cb=None):
        super().__init__()
        self.config = config
        self.controller = controller
        self._emergency_lock_cb = emergency_lock_cb
        self.setWindowTitle("AppGuard Pro")
        self.setMinimumSize(960, 650)
        
        self.qr_path = os.path.join(CONFIG_DIR, "remote_qr.png")
        
        setTheme(Theme.DARK)
        
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(self.size())
        self.splashScreen.show()

        # Initialize Interfaces
        self.dashboard_interface = DashboardInterface(self)
        self.apps_interface = AppLockInterface(self)
        self.groups_interface = GroupsInterface(self)
        self.usb_interface = UsbInterface(self)
        self.settings_interface = SettingsInterface(self)

        self._init_navigation()
        self._init_connections()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)
        
        self.splashScreen.finish()
        self.refresh()

    def _init_navigation(self):
        self.addSubInterface(self.dashboard_interface, FIF.HOME, t("tab_dashboard"))
        self.addSubInterface(self.apps_interface, FIF.APPLICATION, t("tab_apps"))
        self.addSubInterface(self.groups_interface, FIF.FOLDER, t("tab_groups"))
        self.addSubInterface(self.usb_interface, FIF.VPN, t("tab_usb"))
        
        self.addSubInterface(
            self.settings_interface, FIF.SETTING, t("tab_settings"),
            position=NavigationItemPosition.BOTTOM
        )

    def _init_connections(self):
        self.apps_interface.app_added.connect(self._add_app)
        self.apps_interface.app_removed.connect(self._remove_app)
        self.apps_interface.app_selected.connect(self._change_app_pw)
        self.groups_interface.group_added.connect(self._add_group)
        self.groups_interface.group_removed.connect(self._remove_group)
        self.groups_interface.group_selected.connect(self._change_group_pw)
        self.usb_interface.usb_added.connect(self._add_usb)
        self.usb_interface.usb_removed.connect(self._remove_usb)

    def refresh(self):
        apps = self.config.get_protected_apps()
        groups = self.config.get_groups()
        usbs = self.config.get_usb_whitelist()
        
        self.dashboard_interface.update_stats(len(apps), len(groups), len(usbs))
        self.apps_interface.load_apps(apps)
        self.groups_interface.load_groups(groups)
        self.usb_interface.load_usbs(usbs)

    def _rebind_hotkeys(self):
        if self.controller:
            self.controller.bind_hotkeys()
            
    def _update_stealth_mode(self):
        if self.controller:
            self.controller.update_stealth_mode()

    # --- Controller actions ---
    def _add_app(self, name, exe_path):
        pw_dlg = PasswordInputWithStrength(t("dlg_set_pw_title"), f"{name} {t('dlg_set_pw_lbl')}", parent=self)
        if pw_dlg.exec() == pw_dlg.DialogCode.Accepted:
            pw = pw_dlg.get_password()
            self.config.add_protected_app(exe_path, name, pw)
            self.refresh()

    def _remove_app(self, app_id):
        self.config.remove_protected_app(app_id)
        self.refresh()

    def _change_app_pw(self, app_id: str):
        app = self.config.data.get("apps", {}).get(app_id)
        if not app: return
        name = app.get("name", "App")
        pw_dlg = PasswordInputWithStrength(t("dlg_new_pw_title"), f"{name} {t('dlg_new_pw_lbl')}", parent=self)
        if pw_dlg.exec() == pw_dlg.DialogCode.Accepted:
            pw = pw_dlg.get_password()
            self.config.update_app_password(app_id, pw)
            QMessageBox.information(self, t("success_title"), t("dlg_updated_msg"))
            self.refresh()

    def _add_group(self, name):
        pw_dlg = PasswordInputWithStrength(t("dlg_group_pw_title"), f"{name} {t('dlg_group_pw_lbl')}", parent=self)
        if pw_dlg.exec() == pw_dlg.DialogCode.Accepted:
            pw = pw_dlg.get_password()
            self.config.add_group(name, pw, [])
            self.refresh()

    def _remove_group(self, gid):
        self.config.remove_group(gid)
        self.refresh()

    def _change_group_pw(self, gid: str):
        group = self.config.data.get("groups", {}).get(gid)
        if not group: return
        name = group.get("name", "Group")
        pw_dlg = PasswordInputWithStrength(t("dlg_new_pw_title"), f"{name} {t('dlg_new_pw_lbl')}", parent=self)
        if pw_dlg.exec() == pw_dlg.DialogCode.Accepted:
            pw = pw_dlg.get_password()
            self.config.update_group_password(gid, pw)
            QMessageBox.information(self, t("success_title"), t("dlg_updated_msg"))
            self.refresh()

    def _add_usb(self, serial: str, label: str) -> None:
        self.config.add_usb_to_whitelist(serial, label)
        self.refresh()

    def _remove_usb(self, serial: str) -> None:
        self.config.remove_usb_from_whitelist(serial)
        self.refresh()

    def _restart_remote_server(self) -> None:
        """Called by settings when toggling the remote lock server."""
        if self.controller is not None:
            # Delegate to the controller which owns the server lifecycle.
            self.controller._check_settings_update()

    def _emergency_lock_signal(self):
        if hasattr(self, "_emergency_lock_cb") and self._emergency_lock_cb:
            self._emergency_lock_cb()
        else:
            QMessageBox.information(self, "⚡ Emergency Lock", "Emergency lock activated.")
