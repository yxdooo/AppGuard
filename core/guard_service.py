"""
core/guard_service.py — Arka plan process izleme servisi

İzin Hiyerarşisi (en yüksekten en düşüğe):
  1. _session_allowed_exes  : Kullanıcı şifre girdi → o exe TÜM OTURUM boyunca serbest.
                              Chrome gibi çok process açan uygulamalarda sürekli şifre
                              sorulmamasını sağlar. Sadece acil kilit / ekran kilidi
                              ile temizlenir.

  2. _allowed_pids          : Belirli PID'lere tek seferlik izin (yedek güvence).
                              Ölü PID'ler her scan'de temizlenir.

  3. _processing            : Dialog açık olan exe'ler — scan tekrar yakalamaz.

  4. _active_blocks         : Dialog açıkken sürekli çalışan kill thread'leri.
                              Kullanıcı şifre girmeden kapansa bile uygulama çalışamaz.
"""
import json
import os
import subprocess
import threading
import time
from typing import Set, Dict

import psutil
from PyQt6.QtCore import QObject, pyqtSignal

from core.config import Config


class SignalBridge(QObject):
    """Thread-safe Qt signal bridge."""
    show_password_dialog = pyqtSignal(str, str, str, str, str, bool)
    show_notification = pyqtSignal(str, str)


class GuardService(threading.Thread):
    """
    250ms'de bir tüm processleri tarar.
    Korumalı exe açıldığında: yakala → güvenilir şekilde öldür → aktif bloker başlat → sinyal gönder.
    Şifre girilince: o exe oturum boyunca serbest (tekrar şifre sorulmaz).
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
        self._interval = 0.25  # 250ms — hızlı yakalama

    # ── External API ─────────────────────────────────────────────────────

    def set_interval(self, interval: float):
        """Used by the performance monitor to adjust scan frequency."""
        with self._lock:
            self._interval = interval

    def allow_pid(self, pid: int):
        """Belirli bir PID'e izin ver."""
        with self._lock:
            self._allowed_pids.add(pid)

    def session_allow_exe(self, exe_name: str):
        """
        Exe adına OTURUM BAZLI izin ver.
        Kullanıcı şifre doğruladıktan sonra çağrılır.
        Chrome, Discord gibi çok process açan uygulamalarda
        bir sonraki şifre sormayı tamamen engeller.
        Sadece clear_all_pids() (acil kilit / ekran kilidi) ile temizlenir.
        """
        name = exe_name.lower()
        with self._lock:
            import time
            self._session_allowed_exes[name] = time.time()
        # Stop active blocker (dialog closing, no more killing)
        self._stop_active_block(name)

    # Backward compatibility — for old allow_exe calls
    def allow_exe(self, exe_name: str, duration: float = 15.0):
        """Grant session permission (duration is obsolete, session-based)."""
        self.session_allow_exe(exe_name)

    def release_exe(self, exe_name: str):
        """
        Diyalog kapandıktan sonra processing kuyruğundan çıkar.
        Şifre GİRİLMEDİYSE (iptal): bloker durduruluyor ama session allow YOK,
        yani bir sonraki açılış denemesinde tekrar şifre sorulacak.
        """
        name = exe_name.lower()
        with self._lock:
            self._processing.discard(name)
        # Stop blocker if session_allow_exe was not called (cancelled)
        # Blocker already stopped if session_allow_exe was called
        self._stop_active_block(name)

    def clear_all_pids(self):
        """
        Acil kilit veya ekran kilidi: tüm oturum izinlerini sıfırla.
        Sonraki her koruma girişimi için şifre tekrar istenecek.
        """
        with self._lock:
            self._allowed_pids.clear()
            self._session_allowed_exes.clear()
        for name in list(self._active_blocks.keys()):
            self._stop_active_block(name)

    def deauth_exe(self, exe_name: str):
        """Belirli bir exe'nin oturum iznini iptal et (manuel kilit)."""
        with self._lock:
            self._session_allowed_exes.pop(exe_name.lower(), None)

    def get_session_allowed(self) -> Set[str]:
        """Oturum boyunca izin verilen exe'lerin listesi."""
        with self._lock:
            return set(self._session_allowed_exes.keys())

    def stop(self):
        self._running = False
        for name in list(self._active_blocks.keys()):
            self._stop_active_block(name)

    # ── Kill Helpers ─────────────────────────────────────────────────────

    def _kill_process(self, proc) -> bool:
        """
        Process'i güvenilir şekilde öldür.
        psutil.kill() başarısız olursa taskkill /f /pid /t fallback kullanır.
        """
        pid = proc.pid
        # 1. psutil dene
        try:
            proc.kill()
            try:
                proc.wait(timeout=0.3)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass
            return True
        except psutil.NoSuchProcess:
            return True  # Zaten ölmüş
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

    def _kill_by_name(self, exe_name: str):
        """Kill all unauthorized processes with the specified exe name."""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if (proc.info["name"] or "").lower() != exe_name:
                    continue
                pid = proc.info["pid"]
                with self._lock:
                    # Oturum izni varsa dokunma
                    if exe_name in self._session_allowed_exes:
                        return  # All these exes are free, exit early
                    if pid in self._allowed_pids:
                        continue
                self._kill_process(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    # ── Active Blocker ───────────────────────────────────────────────────

    def _start_active_block(self, exe_name: str):
        """
        Dialog açık olduğu sürece exe'yi sürekli öldüren thread.
        Kullanıcı şifre girmese bile uygulama çalışamaz.
        """
        if exe_name in self._active_blocks:
            return  # Already running

        stop_event = threading.Event()
        self._active_blocks[exe_name] = stop_event

        def _blocker():
            while not stop_event.is_set():
                # Stop if session is allowed
                with self._lock:
                    if exe_name in self._session_allowed_exes:
                        break
                self._kill_by_name(exe_name)
                stop_event.wait(0.25)

        t = threading.Thread(target=_blocker, daemon=True, name=f"Blocker-{exe_name}")
        t.start()

    def _stop_active_block(self, exe_name: str):
        event = self._active_blocks.pop(exe_name, None)
        if event:
            event.set()

    # ── Main Loop ────────────────────────────────────────────────────────

    def run(self):
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
        import time
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
                    # 1. Session allowed? → skip completely
                    if pname in self._session_allowed_exes:
                        self._allowed_pids.add(pid)
                        continue
                    # 2. Does this PID have special permission?
                    if pid in self._allowed_pids:
                        continue
                    # 3. Is dialog already open?
                    if pname in self._processing:
                        continue
                    # New catch — process it
                    self._processing.add(pname)
                    open('guard_debug.log', 'a').write(f'MATCHED {pname}\n')

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
                    self.config.log_activity("Engellendi", f"{display_name} açılmaya çalışıldı.")

                # 2. Start active blocker — continuously block while dialog is open
                self._start_active_block(pname)

                # 3. Notify user and prompt for password
                self.sig.show_notification.emit(
                    "🛡️ AppGuard",
                    f'"{display_name}" açılmaya çalışıldı — şifre gerekiyor.',
                )
                self.sig.show_password_dialog.emit(
                    app_id, auth_id, display_name, pexe,
                    json.dumps(cmdline), is_group,
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def _best_match(self, candidates: list, exe_path: str) -> tuple:
        """
        Birden fazla aday varsa exe_path'e göre en iyi eşleşmeyi bul.
        Sıra: Tam path > Klasör eşleşmesi > İlk kayıt
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
