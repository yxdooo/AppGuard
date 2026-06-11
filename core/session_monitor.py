"""
core/session_monitor.py — Windows ekran kilidi tespiti
OpenInputDesktop yöntemiyle her 2 saniyede bir kilit durumunu kontrol eder.
"""
import ctypes
import threading
import time
from typing import Callable


class SessionMonitor(threading.Thread):
    """
    Windows'ta ekran kilitlendiğinde on_lock, tekrar açıldığında on_unlock çağrılır.
    OpenInputDesktop API: kilitliyken çağrı başarısız olur.
    """

    def __init__(self, on_lock: Callable, on_unlock: Callable):
        super().__init__(daemon=True, name="SessionMonitor")
        self.on_lock = on_lock
        self.on_unlock = on_unlock
        self._running = True
        self._was_locked = self._check_locked()

    @staticmethod
    def _check_locked() -> bool:
        user32 = ctypes.windll.user32
        hDesk = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_READOBJECTS
        if hDesk:
            user32.CloseDesktop(hDesk)
            return False
        return True  # Desktop açılamadı = kilitli

    def run(self):
        while self._running:
            try:
                locked = self._check_locked()
                if locked and not self._was_locked:
                    self.on_lock()
                elif not locked and self._was_locked:
                    self.on_unlock()
                self._was_locked = locked
            except Exception:
                pass
            time.sleep(2)

    def stop(self):
        self._running = False
