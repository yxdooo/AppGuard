"""
core/hotkey_manager.py — Küresel kısayol yönetimi (keyboard kütüphanesi)
"""
from typing import Callable


class HotkeyManager:
    """
    Manages global hotkeys.
    """

    def __init__(self):
        self._hotkeys: dict[str, str] = {}
        self._enabled = False

    def register(self, name: str, combo: str, callback: Callable) -> bool:
        """Register a hotkey by name."""
        try:
            import keyboard
            self.remove(name)
            keyboard.add_hotkey(combo, callback, suppress=False)
            self._hotkeys[name] = combo
            self._enabled = True
            return True
        except Exception as exc:
            print(f"[HotkeyManager] Error registering ({combo}): {exc}")
            return False

    def remove(self, name: str):
        if name in self._hotkeys:
            try:
                import keyboard
                keyboard.remove_hotkey(self._hotkeys[name])
            except Exception:
                pass
            del self._hotkeys[name]

    def update(self, name: str, new_combo: str, callback: Callable) -> bool:
        return self.register(name, new_combo, callback)

    def disable(self):
        for name in list(self._hotkeys.keys()):
            self.remove(name)
        self._enabled = False

    @property
    def current(self) -> str | None:
        return self._current

    @property
    def is_active(self) -> bool:
        return self._enabled and self._current is not None
