"""
core/performance_monitor.py — CPU-based adaptive polling interval
"""
import logging
import psutil
import threading
import time

log = logging.getLogger(__name__)


class PerformanceMonitor(threading.Thread):
    def __init__(self, guard_service):
        super().__init__(daemon=True, name="PerformanceMonitor")
        self.guard_service = guard_service
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                # Measure CPU usage over the last 2 seconds.
                cpu = psutil.cpu_percent(interval=2)

                # Increase scan interval if system is under heavy load,
                # decrease when idle — but never below 250 ms to avoid
                # burning CPU on process enumeration itself.
                if cpu > 80:
                    self.guard_service.set_interval(1.5)
                elif cpu > 50:
                    self.guard_service.set_interval(0.8)
                elif cpu > 20:
                    self.guard_service.set_interval(0.3)
                else:
                    self.guard_service.set_interval(0.25)  # minimum: 250 ms
            except Exception:
                # cpu_percent can fail in edge cases; sleep to avoid busy-loop.
                log.exception("PerformanceMonitor error")
                self._stop_event.wait(2)

    def stop(self) -> None:
        """Signal the thread to exit; returns immediately (does not join)."""
        self._stop_event.set()
