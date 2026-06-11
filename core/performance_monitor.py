"""
core/performance_monitor.py — CPU bazlı adaptif tarama sıklığı (Polling Interval)
"""
import psutil
import threading
import time

class PerformanceMonitor(threading.Thread):
    def __init__(self, guard_service):
        super().__init__(daemon=True, name="PerformanceMonitor")
        self.guard_service = guard_service
        self._running = True

    def run(self):
        while self._running:
            try:
                # Measure CPU usage over the last 2 seconds
                cpu = psutil.cpu_percent(interval=2)
                
                # Increase scan interval if system is under heavy load (e.g. gaming, 1.0s)
                # Scan frequently if system is idle (0.3s)
                if cpu > 80:
                    self.guard_service.set_interval(1.5)
                elif cpu > 50:
                    self.guard_service.set_interval(0.8)
                elif cpu > 20:
                    self.guard_service.set_interval(0.3)
                else:
                    self.guard_service.set_interval(0.1)
            except Exception:
                pass

    def stop(self):
        self._running = False
