"""
core/hotkey_manager.py — Global hotkey management (keyboard library)
"""
import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except ImportError:
    # 'keyboard' is optional; hotkeys will be silently disabled if missing.
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

    def register(
        self,
        name: str,
        combo: str,
        callback: Callable,
        on_error: Callable[[str], None] | None = None,
    ) -> bool:
        """Register or replace a global hotkey by *name*.

        Parameters
        ----------
        on_error:
            Optional callback invoked with an error message string if
            registration fails (e.g., insufficient permissions).  Use this
            to show a tray notification for security-critical hotkeys.
        """
        if not _KEYBOARD_AVAILABLE:
            return False
        try:
            self.remove(name)
            _keyboard.add_hotkey(combo, callback, suppress=False)
            self._hotkeys[name] = combo
            self._last_registered = combo
            self._enabled = True
            return True
        except Exception as exc:
            msg = f"[HotkeyManager] Error registering '{combo}': {exc}"
            log.warning(msg)
            if on_error:
                on_error(msg)
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
        self._last_registered = None

    @property
    def last_registered(self) -> Optional[str]:
        """The most-recently successfully registered hotkey combo, or None."""
        return self._last_registered

    @property
    def is_active(self) -> bool:
        """True when at least one hotkey is registered and the manager is enabled."""
        return self._enabled and bool(self._hotkeys)
