"""
main.py — AppGuard Pro Main Entry Point
System tray, guard service, USB monitor, screen lock monitor, global hotkey, widget, performance monitor, remote lock.
"""
import logging
import sys
import os
import json
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSlot

from core.config import Config
from core.guard_service import GuardService, SignalBridge
from core.usb_detector import USBMonitor, get_removable_drives
from core.session_monitor import SessionMonitor
from core.hotkey_manager import HotkeyManager
from core.performance_monitor import PerformanceMonitor
from core.remote_lock import RemoteLockServer
from core.i18n import t, set_lang
from ui.theme import set_accent, get_accent_color, get_style


def _make_icon(color: str, alert: bool = False) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QBrush(QColor("white")))
    p.drawRoundedRect(20, 32, 24, 18, 4, 4)
    p.setPen(QPen(QColor("white"), 4, Qt.PenStyle.SolidLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(22, 20, 20, 20, 0, 180 * 16)
    if alert:
        p.setBrush(QBrush(QColor("#ef4444")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(44, 4, 16, 16)
    p.end()
    return QIcon(pm)


class AppGuardController(QObject):

    def __init__(self, app: QApplication, config: "Config | None" = None):
        super().__init__()
        self.app = app
        self.config = config if config is not None else Config()
        self.main_window = None
        self.usb_available = False
        self._alert_count = 0

        # Load i18n + theme
        set_lang(self.config.get_setting("language", "tr"))
        set_accent(self.config.get_setting("theme", "purple"))

        # Signal bridge
        self.sig = SignalBridge()
        self.sig.show_password_dialog.connect(self._on_password_needed)
        self.sig.show_notification.connect(self._on_notification)

        # Services
        self.guard = GuardService(self.config, self.sig)

        self.usb_monitor = USBMonitor(
            on_connect=self._on_usb_connect,
            on_disconnect=self._on_usb_disconnect,
        )

        self.session_monitor = SessionMonitor(
            on_lock=self._on_screen_lock,
            on_unlock=self._on_screen_unlock,
        )

        self.hotkey_mgr = HotkeyManager()
        self.perf_monitor = PerformanceMonitor(self.guard)

        # Remote lock server
        self.remote_server = None
        if self.config.get_setting("remote_lock_enabled", False):
            token = self._get_remote_token()
            self.remote_server = RemoteLockServer(
                auth_token=token,
                port=self.config.get_setting("remote_lock_port", 8080),
            )
            self.remote_server.signals.lock_requested.connect(
                self._emergency_lock, Qt.ConnectionType.QueuedConnection
            )
            self.remote_server.signals.server_error.connect(
                lambda msg: self.tray.showMessage(
                    "AppGuard — Remote Lock Error", msg,
                    QSystemTrayIcon.MessageIcon.Warning, 5000,
                )
            )

        # System tray
        self._normal_icon = _make_icon(get_accent_color())
        self._alert_icon  = _make_icon("#ef4444", alert=True)
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._normal_icon)
        self.tray.setToolTip("AppGuard Pro")
        self._setup_tray_menu()
        self.tray.show()

        # Tray animation timer
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_tray)
        self._blink_state = False

        self._settings_watcher = QTimer(self)
        self._settings_watcher.timeout.connect(self._check_settings_update)
        self._settings_watcher.start(2000)

        self._check_usbs()

    # ── Tray ─────────────────────────────────────────────────────────────
    def _setup_tray_menu(self):
        menu = QMenu()
        menu.setStyleSheet(get_style())
        open_act = menu.addAction("🛡️  Open Panel")
        open_act.triggered.connect(self.show_dashboard)
        
        menu.addSeparator()
        lock_act = menu.addAction("⚡  Emergency Lock")
        lock_act.triggered.connect(self._emergency_lock)
        menu.addSeparator()
        quit_act = menu.addAction("✕  Exit")
        quit_act.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)

    def _on_tray_click(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_dashboard()

    def _start_blink(self):
        self._alert_count += 1
        if not self._blink_timer.isActive():
            self._blink_timer.start(500)

    def _stop_blink(self):
        self._alert_count = max(0, self._alert_count - 1)
        if self._alert_count == 0:
            self._blink_timer.stop()
            self.tray.setIcon(self._normal_icon)
            self.tray.setToolTip("AppGuard Pro")

    def _blink_tray(self):
        self._blink_state = not self._blink_state
        self.tray.setIcon(self._alert_icon if self._blink_state else self._normal_icon)

    # ── Dashboard ────────────────────────────────────────────────────────
    @pyqtSlot()
    def show_dashboard(self):
        from ui.password_dialog import PasswordDialog
        from ui.main_window import MainWindow

        if self.main_window and self.main_window.isVisible():
            self.main_window.raise_(); self.main_window.activateWindow()
            return

        dlg = PasswordDialog(
            app_id="__master__", auth_id="__master__",
            app_name="AppGuard Pro", config=self.config,
            is_master=True, usb_available=self.usb_available,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        # Cache the verified plaintext password on the config object for the
        # duration of this session so the encrypted notepad can derive its key
        # from the raw password rather than from the stored hash.
        self.config._session_master_pw = dlg.get_password()

        if not self.main_window:
            self.main_window = MainWindow(
                self.config, 
                controller=self, 
                emergency_lock_cb=self._emergency_lock
            )

        self.main_window.refresh()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()


    # ── Protected App Password Dialog ────────────────────────────────────
    @pyqtSlot(str, str, str, str, str, bool)
    def _on_password_needed(self, app_id: str, auth_id: str, app_name: str,
                             exe_path: str, cmdline_json: str, is_group: bool):
        from ui.password_dialog import PasswordDialog

        self._start_blink()

        dlg = PasswordDialog(
            app_id=app_id, auth_id=auth_id, app_name=app_name,
            config=self.config, is_master=False, is_group=is_group,
            exe_path=exe_path, usb_available=self.usb_available,
        )

        if dlg.exec() == dlg.DialogCode.Accepted:
            exe_name = os.path.basename(exe_path).lower()
            # Grant session permission so multi-process apps (Chrome, Discord)
            # are not re-prompted until emergency lock or screen lock.
            self.guard.session_allow_exe(exe_name)
            try:
                cmdline = json.loads(cmdline_json)
                if cmdline:
                    cwd = os.path.dirname(exe_path) if exe_path else None
                    proc = subprocess.Popen(cmdline, cwd=cwd)
                    self.guard.allow_pid(proc.pid)
            except Exception as exc:
                self._on_notification("AppGuard", f"Error: {exc}")
        # Remove from processing list on both cancel and success
        self.guard.release_exe(os.path.basename(exe_path).lower())
        self._stop_blink()


    # ── Notification ─────────────────────────────────────────────────────
    @pyqtSlot(str, str)
    def _on_notification(self, title: str, message: str):
        if self.config.get_setting("notifications_enabled", True):
            self.tray.showMessage(title, message,
                                  QSystemTrayIcon.MessageIcon.Warning, 4000)

    # ── Screen Lock ──────────────────────────────────────────────────────
    def _on_screen_lock(self):
        if self.config.get_setting("lock_on_screen_lock", True):
            self.guard.clear_all_pids()
            if hasattr(self.config, "_session_master_pw"):
                delattr(self.config, "_session_master_pw")
            self._on_notification("🔒 AppGuard", "Screen locked, permissions reset.")
            self.config.log_activity("Screen Locked", "All session permissions reset.")

    def _on_screen_unlock(self):
        pass

    # ── Emergency Lock ───────────────────────────────────────────────────
    def _emergency_lock(self):
        self.guard.clear_all_pids()
        if hasattr(self.config, "_session_master_pw"):
            delattr(self.config, "_session_master_pw")
        self._on_notification("⚡ AppGuard", "System emergency locked!")
        self.config.log_activity("Emergency Lock", "All permissions reset.")

    # ── USB ──────────────────────────────────────────────────────────────
    def _check_usbs(self):
        for d in get_removable_drives():
            if self.config.is_usb_whitelisted(d["serial"]):
                self.usb_available = True
                break

    def _on_usb_connect(self, info: dict):
        if self.config.is_usb_whitelisted(info["serial"]):
            self.usb_available = True
            self.sig.show_notification.emit("🔑 AppGuard", f"Trusted USB: {info['label']}")
            self.config.log_activity("USB Connected", info['label'])

    def _on_usb_disconnect(self, serial: str):
        if self.config.is_usb_whitelisted(serial):
            self.usb_available = any(
                self.config.is_usb_whitelisted(d["serial"])
                for d in get_removable_drives())
            if not self.usb_available:
                self.sig.show_notification.emit("🔑 AppGuard", "Trusted USB disconnected.")
                self.config.log_activity("USB Disconnected", serial)

    # ── Setting Updates ──────────────────────────────────────────────────
    def _check_settings_update(self):
        """Called every 2 s to react to settings changes made in the UI."""
        # Remote server: start/stop based on the current setting.
        remote_enabled = self.config.get_setting("remote_lock_enabled", False)
        port = self.config.get_setting("remote_lock_port", 8080)
        if remote_enabled and not self.remote_server:
            token = self._get_remote_token()
            self.remote_server = RemoteLockServer(auth_token=token, port=port)
            self.remote_server.signals.lock_requested.connect(self._emergency_lock)
            self.remote_server.start()
        elif not remote_enabled and self.remote_server:
            self.remote_server.stop()
            self.remote_server = None

    # ── Start / Stop ─────────────────────────────────────────────────────
    def bind_hotkeys(self):
        hk_emergency = self.config.get_setting("emergency_hotkey", "ctrl+shift+l")
        self.hotkey_mgr.register("emergency", hk_emergency, self._emergency_lock)
        
        hk_stealth = self.config.get_setting("stealth_hotkey", "ctrl+shift+h")
        self.hotkey_mgr.register("stealth", hk_stealth, self._toggle_stealth_visibility)

    def _toggle_stealth_visibility(self):
        if self.config.get_setting("stealth_mode_enabled", False):
            if self.tray.isVisible():
                self.tray.hide()
                if self.main_window: self.main_window.hide()
            else:
                self.tray.show()
                # Automatically prompt for password when making it visible again
                self.show_dashboard()

    def update_stealth_mode(self):
        is_stealth = self.config.get_setting("stealth_mode_enabled", False)
        if is_stealth:
            self.tray.hide()
            if self.main_window: self.main_window.hide()
        else:
            self.tray.show()

    def start_services(self):
        self.bind_hotkeys()
        self.update_stealth_mode()
        self.guard.start()
        self.usb_monitor.start()
        self.session_monitor.start()
        self.perf_monitor.start()
        if self.remote_server:
            self.remote_server.start()

    def _quit(self) -> None:
        self.guard.stop()
        self.session_monitor.stop()  # was missing — would leave thread running
        self.usb_monitor.stop()
        self.perf_monitor.stop()
        if self.remote_server:
            self.remote_server.stop()
        self.hotkey_mgr.disable()
        self.tray.hide()
        self.app.quit()

    def _get_remote_token(self) -> str:
        import secrets as _secrets
        token = self.config.get_setting("remote_lock_token")
        if not token:
            token = _secrets.token_urlsafe(16)
            self.config.set_setting("remote_lock_token", token)
        return token


# ─────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("AppGuard")

    # Create the single Config instance that is shared everywhere.
    # AppGuardController will reuse it rather than creating its own.
    config = Config()
    # AppGuardController.__init__() already calls set_lang/set_accent when it
    # reads config, so we only call them here for the setup dialog (which runs
    # before the controller is created). No duplicate calls needed afterward.
    set_lang(config.get_setting("language", "tr"))
    set_accent(config.get_setting("theme", "purple"))

    if not config.has_master_password():
        from ui.setup_dialog import SetupDialog
        setup = SetupDialog(config)
        if setup.exec() != setup.DialogCode.Accepted:
            sys.exit(0)

    ctrl = AppGuardController(app, config=config)
    ctrl.start_services()

    if "--show-dashboard" in sys.argv:
        QTimer.singleShot(300, ctrl.show_dashboard)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
