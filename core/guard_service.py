"""
Core background service responsible for monitoring and blocking processes.

Permission Hierarchy:
  1. _session_allowed_exes : Apps allowed for the duration of the session.
  2. _allowed_pids         : Short-lived explicit PIDs allowed to run.
  3. _processing           : Apps currently showing the password dialog.
  4. _active_blocks        : Threads continuously killing apps while dialog is open.
"""
import json
import os
import subprocess
import threading
import time

import psutil
from PyQt6.QtCore import QObject, pyqtSignal

from core.config import Config


class SignalBridge(QObject):
    """Thread-safe Qt signal bridge."""
    show_password_dialog = pyqtSignal(str, str, str, str, str, bool)
    show_notification = pyqtSignal(str, str)


class GuardService(threading.Thread):
    """
    Background worker that monitors running processes every 250ms.
    Detects protected applications, suspends them, and triggers the password dialog.
    """

    def __init__(self, config: Config, bridge: SignalBridge):
        super().__init__(daemon=True, name="GuardService")
        self.config = config
        self.sig = bridge
        self._running = True

        # Exes allowed for the session (password verified, don't ask again)
        self._session_allowed_exes: dict[str, float] = {}

        # Allow specific PIDs (backup, short-lived)
        self._allowed_pids: Set[int] = set()

        # Exes with currently open dialog (scan won't catch again)
        self._processing: Set[str] = set()

        # Kill threads running while dialog is open: exe -> stop_event
        self._active_blocks: Dict[str, threading.Event] = {}

        self._lock = threading.Lock()
        self._interval = 0.25  # 250ms â€” fast catch

    # â”€â”€ External API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def set_interval(self, interval: float):
        """Used by the performance monitor to adjust scan frequency."""
        with self._lock:
            self._interval = interval

    def allow_pid(self, pid: int) -> None:
        """Grant a specific PID permission to run."""
        with self._lock:
            self._allowed_pids.add(pid)

    def session_allow_exe(self, exe_name: str) -> None:
        """
        Give SESSION-BASED permission to exe name.
        Called after user verifies password.
        In multi-process apps like Chrome, Discord
        completely prevents the next password prompt.
        Only clear_all_pids() (emergency lock / screen lock) resets this.
        """
        name = exe_name.lower()
        with self._lock:
            self._session_allowed_exes[name] = time.time()
        # Stop active blocker (dialog closing, no more killing)
        self._stop_active_block(name)

    # Backward compatibility -> for old allow_exe calls
    def allow_exe(self, exe_name: str, duration: float = 15.0):
        """Grant session permission (duration is obsolete, session-based)."""
        self.session_allow_exe(exe_name)

    def release_exe(self, exe_name: str):
        """
        Remove from processing queue after dialog closes.
        If password NOT ENTERED (cancel): blocker stopped but NO session allow,
        so password will be asked again on the next launch attempt.
        """
        name = exe_name.lower()
        with self._lock:
            self._processing.discard(name)
        # Stop blocker if session_allow_exe was not called (cancelled)
        # Blocker already stopped if session_allow_exe was called
        self._stop_active_block(name)

    def clear_all_pids(self):
        """
        Emergency lock or screen lock: reset all session permissions.
        Password will be asked again for every next protection attempt.
        """
        with self._lock:
            self._allowed_pids.clear()
            self._session_allowed_exes.clear()
        for name in list(self._active_blocks.keys()):
            self._stop_active_block(name)

    def deauth_exe(self, exe_name: str) -> None:
        """Revoke session permission for a specific exe (manual lock)."""
        with self._lock:
            self._session_allowed_exes.pop(exe_name.lower(), None)

    def get_session_allowed(self) -> set[str]:
        """Return the set of exe names allowed for the current session."""
        with self._lock:
            return set(self._session_allowed_exes.keys())

    def stop(self):
        self._running = False
        for name in list(self._active_blocks.keys()):
            self._stop_active_block(name)

    # â”€â”€ Kill Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _kill_process(self, proc: psutil.Process) -> bool:
        """
        Reliably kill the process.
        If psutil.kill() fails, falls back to taskkill /f /pid /t.
        """
        pid = proc.pid
        # 1. Try psutil first
        try:
            proc.kill()
            try:
                proc.wait(timeout=0.3)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass
            return True
        except psutil.NoSuchProcess:
            return True  # Already dead
        except psutil.ZombieProcess:
            return True
        except (psutil.AccessDenied, Exception):
            pass

        # 2. taskkill fallback
        try:
            result = subprocess.run(
                ["taskkill", "/f", "/pid", str(pid), "/t"],
                capture_output=True, timeout=3,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception:
            return False

    def _kill_by_name(self, exe_name: str) -> None:
        """Kill all unauthorized processes with the specified exe name."""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if (proc.info["name"] or "").lower() != exe_name:
                    continue
                pid = proc.info["pid"]
                with self._lock:
                    # If the session granted permission, leave all instances alone.
                    if exe_name in self._session_allowed_exes:
                        return
                    if pid in self._allowed_pids:
                        continue
                self._kill_process(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    # â”€â”€ Active Blocker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _start_active_block(self, exe_name: str) -> None:
        """
        Start a daemon thread that continuously kills *exe_name* while the
        password dialog is open, preventing the app from sneaking through.
        """
        with self._lock:
            # Check-then-act under the lock to prevent two threads from
            # starting duplicate blockers for the same exe.
            if exe_name in self._active_blocks:
                return
            stop_event = threading.Event()
            self._active_blocks[exe_name] = stop_event

        def _scan_and_kill_run():
            while not stop_event.is_set():
                with self._lock:
                    if exe_name in self._session_allowed_exes:
                        break
                self._kill_by_name(exe_name)
                stop_event.wait(0.25)

        blocker = threading.Thread(
            target=_scan_and_kill_run,
            daemon=True,
            name=f"Blocker-{exe_name}",
        )
        blocker.start()

    def _stop_active_block(self, exe_name: str):
        event = self._active_blocks.pop(exe_name, None)
        if event:
            event.set()

    # â”€â”€ Main Loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def run(self) -> None:
        while self._running:
            try:
                self._scan()
            except Exception:
                pass
            time.sleep(self._interval)

    def _scan(self):
        protected = self.config.get_protected_apps()
        if not protected:
            return

        # {exe_basename_lower: [(app_id, app_data), ...]}
        lookup: Dict[str, list] = {}
        for app_id, app in protected.items():
            if not app.get("enabled", True) or not self.config.is_app_enabled_in_profile(app_id):
                continue
            bn = os.path.basename(app.get("exe_path", "")).lower()
            if bn:
                lookup.setdefault(bn, []).append((app_id, app))

        if not lookup:
            return

        # Clear dead PIDs
        with self._lock:
            self._allowed_pids = {p for p in self._allowed_pids if psutil.pid_exists(p)}

        try:
            procs = list(psutil.process_iter(["pid", "name", "exe"]))
        except Exception:
            return

        running_names = {(p.info["name"] or "").lower() for p in procs}
        with self._lock:
            to_remove = set()
            for exe, grant_time in self._session_allowed_exes.items():
                if exe not in running_names and (time.time() - grant_time) > 5.0:
                    to_remove.add(exe)
            for exe in to_remove:
                del self._session_allowed_exes[exe]

        for proc in procs:
            try:
                pname = (proc.info["name"] or "").lower()
                pexe  = proc.info["exe"] or ""
                pid   = proc.info["pid"]

                if pname not in lookup:
                    continue

                with self._lock:
                    # 1. Session allowed? -> skip completely
                    if pname in self._session_allowed_exes:
                        self._allowed_pids.add(pid)
                        continue
                    # 2. Does this PID have special permission?
                    if pid in self._allowed_pids:
                        continue
                    # 3. Is dialog already open?
                    if pname in self._processing:
                        continue
                    # New process caught â€” begin blocking and show dialog.
                    self._processing.add(pname)

                # Find the best match
                candidates = lookup[pname]
                matched_id, matched_app = self._best_match(candidates, pexe)
                app_id = matched_id
                auth_id, display_name, is_group = self.config.get_auth_target(app_id)

                # Get command line
                try:
                    cmdline = proc.cmdline()
                except Exception:
                    cmdline = [pexe] if pexe else [pname]

                # 1. Kill instantly
                killed = self._kill_process(proc)
                if killed:
                    self.config.log_activity("Blocked", f"Attempted to open {display_name}.")

                # 2. Start active blocker -> continuously block while dialog is open
                self._start_active_block(pname)

                # 3. Notify user and prompt for password
                self.sig.show_notification.emit(
                    "ğŸ›¡ï¸ AppGuard",
                    f'"{display_name}" attempted to launch â€” password required.',
                )
                self.sig.show_password_dialog.emit(
                    app_id, auth_id, display_name, pexe,
                    json.dumps(cmdline), is_group,
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def _best_match(self, candidates: list, exe_path: str) -> tuple:
        """
        If multiple candidates, find best match by exe_path.
        Order: Exact path > Folder match > First record
        """
        if len(candidates) == 1:
            return candidates[0]

        exe_lower = exe_path.lower() if exe_path else ""

        for app_id, app in candidates:
            registered = app.get("exe_path", "").lower()
            if registered and exe_lower and registered == exe_lower:
                return app_id, app

        for app_id, app in candidates:
            registered = app.get("exe_path", "").lower()
            if registered and exe_lower:
                reg_dir = os.path.dirname(registered)
                if reg_dir and reg_dir in exe_lower:
                    return app_id, app

        return candidates[0]

