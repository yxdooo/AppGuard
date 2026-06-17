"""
core/session_monitor.py — Windows screen lock detection.
Checks lock status every 2 seconds via OpenInputDesktop method.
"""
import ctypes
import threading
import time
from typing import Callable


class SessionMonitor(threading.Thread):
    """
    Calls on_lock when Windows screen locks, on_unlock when unlocked.
    OpenInputDesktop API: call fails when locked.
    """

    def __init__(self, on_lock: Callable[[], None], on_unlock: Callable[[], None]) -> None:
        super().__init__(daemon=True, name="SessionMonitor")
        self.on_lock = on_lock
        self.on_unlock = on_unlock
        self._stop_event = threading.Event()
        try:
            self._was_locked = self._check_locked()
        except Exception:
            self._was_locked = False

    @staticmethod
    def _check_locked() -> bool:
        user32 = ctypes.windll.user32
        hDesk = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_READOBJECTS
        if hDesk:
            user32.CloseDesktop(hDesk)
            return False
        return True  # Desktop could not be opened = locked

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                locked = self._check_locked()
                if locked and not self._was_locked:
                    self.on_lock()
                elif not locked and self._was_locked:
                    self.on_unlock()
                self._was_locked = locked
            except Exception:
                pass
            # Use Event.wait() so stop() wakes us immediately.
            self._stop_event.wait(2)

    def stop(self) -> None:
        """Signal the monitor to stop; returns immediately."""
        self._stop_event.set()
