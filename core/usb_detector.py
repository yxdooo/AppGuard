"""
core/usb_detector.py — USB drive connect/disconnect monitoring
"""
import string
import threading
import time
from typing import Callable, Set

try:
    import win32api
    import win32file
    _WIN32 = True
except ImportError:
    _WIN32 = False


def get_removable_drives() -> list[dict]:
    """Returns a list of plugged removable drives."""
    drives = []
    if not _WIN32:
        return drives

    bitmask = win32api.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not (bitmask & (1 << i)):
            continue
        drive = f"{letter}:\\"
        try:
            dtype = win32file.GetDriveType(drive)
            if dtype == win32file.DRIVE_REMOVABLE:
                try:
                    vol_name, vol_serial, *_ = win32api.GetVolumeInformation(drive)
                    drives.append(
                        {
                            "drive": drive,
                            "letter": letter,
                            "label": vol_name or f"USB ({letter}:)",
                            "serial": str(vol_serial),
                        }
                    )
                except Exception:
                    pass
        except Exception:
            pass
    return drives


class USBMonitor(threading.Thread):
    """Monitors USB plug/unplug events in the background."""

    def __init__(self, on_connect: Callable[[dict], None], on_disconnect: Callable[[str], None]):
        super().__init__(daemon=True, name="USBMonitor")
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self._running = True
        self._known: dict[str, dict] = {
            d["serial"]: d for d in get_removable_drives()
        }

    def run(self):
        while self._running:
            try:
                current = {d["serial"]: d for d in get_removable_drives()}

                for serial, info in current.items():
                    if serial not in self._known:
                        self.on_connect(info)

                for serial in list(self._known):
                    if serial not in current:
                        self.on_disconnect(serial)

                self._known = current
            except Exception:
                pass
            time.sleep(1.5)

    def stop(self):
        self._running = False
