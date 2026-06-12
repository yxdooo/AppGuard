"""
core/hotkey_manager.py — Global hotkey management (keyboard library)
"""
from typing import Callable, Optional

try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except Exception:
    _KEYBOARD_AVAILABLE = False
    _keyboard = None  # type: ignore


class HotkeyManager:
    """
    Manages global hotkeys.
    """

    def __init__(self) -> None:
        self._hotkeys: dict[str, str] = {}  # name -> combo
        self._enabled: bool = False
        self._current: Optional[str] = None  # most-recently registered combo

    def register(self, name: str, combo: str, callback: Callable) -> bool:
        """Register or replace a global hotkey by *name*."""
        if not _KEYBOARD_AVAILABLE:
            return False
        try:
            self.remove(name)
            _keyboard.add_hotkey(combo, callback, suppress=False)
            self._hotkeys[name] = combo
            self._current = combo
            self._enabled = True
            return True
        except Exception as exc:
            print(f"[HotkeyManager] Error registering '{combo}': {exc}")
            return False

    def remove(self, name: str) -> None:
        if name in self._hotkeys:
            try:
                if _KEYBOARD_AVAILABLE:
                    _keyboard.remove_hotkey(self._hotkeys[name])
            except Exception:
                pass
            del self._hotkeys[name]

    def update(self, name: str, new_combo: str, callback: Callable) -> bool:
        return self.register(name, new_combo, callback)

    def disable(self) -> None:
        """Unregister all hotkeys."""
        for name in list(self._hotkeys.keys()):
            self.remove(name)
        self._enabled = False
        self._current = None

    @property
    def current(self) -> Optional[str]:
        """The most-recently registered hotkey combo, or None."""
        return self._current

    @property
    def is_active(self) -> bool:
        """True when at least one hotkey is registered and the manager is enabled."""
        return self._enabled and bool(self._hotkeys)
