"""
core/config.py — Configuration management
Passwords, lock status, USB whitelist, groups and app settings.
"""
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from core.crypto import hash_password, verify_password, get_machine_key, encrypt_data, decrypt_data

CONFIG_DIR = Path(os.environ.get("APPDATA", ".")) / "AppGuard"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENC_CONFIG_FILE = CONFIG_DIR / "config.ag"
KEY_FILE = CONFIG_DIR / "machine.key"


def _default() -> dict:
    return {
        "master_password": None,
        "protected_apps": {},
        "groups": {},
        "usb_whitelist": [],
        "profiles": {
            "default": {"name": "Default", "disabled_apps": []}
        },
        "active_profile": "default",
        "activity_log": [],
        "settings": {
            "start_with_windows": False,
            "notifications_enabled": True,
            "lock_on_screen_lock": True,
            "language": "tr",
            "theme": "purple",
            "emergency_hotkey": "ctrl+shift+l",
            "guardian_enabled": False,
            "remote_lock_enabled": False,
        },
    }


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        # Fill missing fields (for older config files)
        for k, v in _default()["settings"].items():
            self.data.setdefault("settings", {}).setdefault(k, v)
        self.data.setdefault("groups", {})
        self.data.setdefault("profiles", {"default": {"name": "Default", "disabled_apps": []}})
        self.data.setdefault("active_profile", "default")
        self.data.setdefault("activity_log", [])

    # ── I/O ──────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        # 1. Try loading encrypted configuration (AES-256-GCM)
        if ENC_CONFIG_FILE.exists():
            try:
                key = get_machine_key(str(KEY_FILE))
                with open(ENC_CONFIG_FILE, "rb") as f:
                    decrypted = decrypt_data(f.read(), key)
                return json.loads(decrypted.decode("utf-8"))
            except Exception as e:
                import traceback
                print(f"Sifreli config yuklenemedi: {e}\n{traceback.format_exc()}")
        
        # 2. Is there a legacy plaintext config? (Auto Migration)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Try saving to the new encrypted system
                self.data = data
                self.save()
                
                # Delete old plaintext file for security (to protect privacy)
                try:
                    os.remove(CONFIG_FILE)
                except Exception:
                    pass
                    
                return data
            except Exception:
                pass
                
        return _default()

    def save(self):
        try:
            key = get_machine_key(str(KEY_FILE))
            raw_data = json.dumps(self.data, ensure_ascii=False).encode("utf-8")
            encrypted = encrypt_data(raw_data, key)
            
            with open(ENC_CONFIG_FILE, "wb") as f:
                f.write(encrypted)
        except Exception as e:
            print(f"Config kaydedilemedi: {e}")

    # ── Master Password ──────────────────────────────────────────────────
    def has_master_password(self) -> bool:
        return self.data.get("master_password") is not None

    def set_master_password(self, pw: str):
        # Salt is generated internally by Argon2; no external salt needed.
        self.data["master_password"] = {"hash": hash_password(pw)}
        self.save()

    def verify_master_password(self, pw: str) -> bool:
        mp = self.data.get("master_password")
        if not mp:
            return True
        is_valid, needs_rehash = verify_password(pw, mp["hash"], mp.get("salt"))
        if is_valid and needs_rehash:
            # Transparently migrate legacy SHA-256 hash to Argon2id.
            self.set_master_password(pw)
        return is_valid

    # ── Protected Apps ───────────────────────────────────────────────────
    def add_protected_app(self, exe_path: str, name: str, pw: str, hint: str = "") -> str:
        app_id = str(uuid.uuid4())
        self.data["protected_apps"][app_id] = {
            "exe_path": exe_path,
            "name": name,
            "password_hash": hash_password(pw),
            "hint": hint,
            "enabled": True,
            "failed_attempts": 0,
            "lockout_until": None,
            "usb_only_mode": False,
            "last_accessed": None,
        }
        self.save()
        return app_id

    def get_protected_apps(self) -> dict:
        return self.data.get("protected_apps", {})

    def remove_protected_app(self, app_id: str):
        self.data["protected_apps"].pop(app_id, None)
        # Remove from groups too
        for g in self.data.get("groups", {}).values():
            ids: list = g.get("app_ids", [])
            if app_id in ids:
                ids.remove(app_id)
        self.save()

    def toggle_app(self, app_id: str):
        app = self.data["protected_apps"].get(app_id)
        if app:
            app["enabled"] = not app.get("enabled", True)
            self.save()

    # ── Password Verification (App) ──────────────────────────────────────
    def verify_app_password(self, app_id: str, pw: str) -> bool:
        app = self.data["protected_apps"].get(app_id)
        if not app:
            return False
        is_valid, needs_rehash = verify_password(pw, app["password_hash"], app.get("salt"))
        if is_valid and needs_rehash:
            self.set_app_password(app_id, pw)
        return is_valid

    def set_app_password(self, app_id: str, pw: str):
        app = self.data["protected_apps"].get(app_id)
        if not app:
            return
        app.update({"password_hash": hash_password(pw),
                    "failed_attempts": 0, "lockout_until": None, "usb_only_mode": False})
        self.save()

    # ── Lock Management (App) ────────────────────────────────────────────
    def record_failed_attempt(self, app_id: str):
        app = self.data["protected_apps"].get(app_id)
        if not app:
            return
        app["failed_attempts"] = app.get("failed_attempts", 0) + 1
        n = app["failed_attempts"]
        if n >= 10:
            app["usb_only_mode"] = True
        elif n >= 9:
            app["lockout_until"] = (datetime.now() + timedelta(minutes=30)).isoformat()
        elif n >= 6:
            app["lockout_until"] = (datetime.now() + timedelta(minutes=10)).isoformat()
        elif n >= 3:
            app["lockout_until"] = (datetime.now() + timedelta(minutes=2)).isoformat()
        self.save()

    def record_success(self, app_id: str):
        app = self.data["protected_apps"].get(app_id)
        if not app:
            return
        app.update({"failed_attempts": 0, "lockout_until": None,
                    "usb_only_mode": False, "last_accessed": datetime.now().isoformat()})
        self.save()

    def get_lockout_status(self, app_id: str) -> dict:
        app = self.data["protected_apps"].get(app_id)
        if not app:
            return {"locked": False, "reason": None, "remaining_seconds": 0, "attempts": 0}
        n = app.get("failed_attempts", 0)
        if app.get("usb_only_mode"):
            return {"locked": True, "reason": "usb_only", "remaining_seconds": 0, "attempts": n}
        lu = app.get("lockout_until")
        if lu:
            dt = datetime.fromisoformat(lu)
            rem = (dt - datetime.now()).total_seconds()
            if rem > 0:
                return {"locked": True, "reason": "timer", "remaining_seconds": int(rem), "attempts": n}
            app["lockout_until"] = None
            self.save()
        return {"locked": False, "reason": None, "remaining_seconds": 0, "attempts": n}

    # ── Groups ───────────────────────────────────────────────────────────
    def add_group(self, name: str, pw: str, app_ids: list[str]) -> str:
        gid = str(uuid.uuid4())
        self.data["groups"][gid] = {
            "name": name,
            "password_hash": hash_password(pw),
            "app_ids": app_ids,
            "enabled": True,
            "failed_attempts": 0,
            "lockout_until": None,
            "usb_only_mode": False,
        }
        self.save()
        return gid

    def get_groups(self) -> dict:
        return self.data.get("groups", {})

    def remove_group(self, gid: str):
        self.data["groups"].pop(gid, None)
        self.save()

    def set_group_password(self, gid: str, pw: str):
        g = self.data["groups"].get(gid)
        if not g:
            return
        g.update({"password_hash": hash_password(pw),
                  "failed_attempts": 0, "lockout_until": None, "usb_only_mode": False})
        self.save()

    def set_group_apps(self, gid: str, app_ids: list[str]):
        g = self.data["groups"].get(gid)
        if g:
            g["app_ids"] = app_ids
            self.save()

    def verify_group_password(self, gid: str, pw: str) -> bool:
        g = self.data["groups"].get(gid)
        if not g:
            return False
        is_valid, needs_rehash = verify_password(pw, g["password_hash"], g.get("salt"))
        if is_valid and needs_rehash:
            self.set_group_password(gid, pw)
        return is_valid

    def get_group_lockout_status(self, gid: str) -> dict:
        g = self.data["groups"].get(gid)
        if not g:
            return {"locked": False, "reason": None, "remaining_seconds": 0, "attempts": 0}
        n = g.get("failed_attempts", 0)
        if g.get("usb_only_mode"):
            return {"locked": True, "reason": "usb_only", "remaining_seconds": 0, "attempts": n}
        lu = g.get("lockout_until")
        if lu:
            dt = datetime.fromisoformat(lu)
            rem = (dt - datetime.now()).total_seconds()
            if rem > 0:
                return {"locked": True, "reason": "timer", "remaining_seconds": int(rem), "attempts": n}
            g["lockout_until"] = None
            self.save()
        return {"locked": False, "reason": None, "remaining_seconds": 0, "attempts": n}

    def record_group_failed(self, gid: str):
        g = self.data["groups"].get(gid)
        if not g:
            return
        g["failed_attempts"] = g.get("failed_attempts", 0) + 1
        n = g["failed_attempts"]
        if n >= 10:
            g["usb_only_mode"] = True
        elif n >= 9:
            g["lockout_until"] = (datetime.now() + timedelta(minutes=30)).isoformat()
        elif n >= 6:
            g["lockout_until"] = (datetime.now() + timedelta(minutes=10)).isoformat()
        elif n >= 3:
            g["lockout_until"] = (datetime.now() + timedelta(minutes=2)).isoformat()
        self.save()

    def record_group_success(self, gid: str):
        g = self.data["groups"].get(gid)
        if g:
            g.update({"failed_attempts": 0, "lockout_until": None, "usb_only_mode": False})
            self.save()

    def get_auth_target(self, app_id: str) -> tuple[str, str, bool]:
        """
        Returns the authentication target for the application.
        Returns: (effective_id, display_name, is_group)
        """
        for gid, g in self.data.get("groups", {}).items():
            if app_id in g.get("app_ids", []) and g.get("enabled", True):
                return gid, g.get("name", "Group"), True
        app = self.data["protected_apps"].get(app_id, {})
        return app_id, app.get("name", app_id), False

    # ── USB Whitelist ────────────────────────────────────────────────────
    def add_usb_to_whitelist(self, serial: str, label: str):
        if not any(u["serial"] == serial for u in self.data["usb_whitelist"]):
            self.data["usb_whitelist"].append({"serial": serial, "label": label})
            self.save()

    def remove_usb_from_whitelist(self, serial: str):
        self.data["usb_whitelist"] = [u for u in self.data["usb_whitelist"] if u["serial"] != serial]
        self.save()

    def is_usb_whitelisted(self, serial: str) -> bool:
        return any(u["serial"] == serial for u in self.data["usb_whitelist"])

    def get_usb_whitelist(self) -> list:
        return self.data.get("usb_whitelist", [])

    # ── Settings ─────────────────────────────────────────────────────────
    def get_setting(self, key: str, default=None):
        return self.data.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value):
        self.data.setdefault("settings", {})[key] = value
        self.save()

    # ── Profiles ─────────────────────────────────────────────────────────
    def get_profiles(self) -> dict:
        return self.data.get("profiles", {})

    def get_active_profile(self) -> str:
        return self.data.get("active_profile", "default")

    def set_active_profile(self, profile_id: str):
        if profile_id in self.data.get("profiles", {}):
            self.data["active_profile"] = profile_id
            self.save()

    def is_app_enabled_in_profile(self, app_id: str) -> bool:
        pid = self.get_active_profile()
        profile = self.data.get("profiles", {}).get(pid, {})
        disabled = profile.get("disabled_apps", [])
        return app_id not in disabled

    def toggle_app_in_profile(self, profile_id: str, app_id: str):
        profile = self.data.get("profiles", {}).get(profile_id)
        if profile:
            disabled = profile.setdefault("disabled_apps", [])
            if app_id in disabled:
                disabled.remove(app_id)
            else:
                disabled.append(app_id)
            self.save()

    def add_profile(self, name: str) -> str:
        pid = str(uuid.uuid4())
        self.data.setdefault("profiles", {})[pid] = {"name": name, "disabled_apps": []}
        self.save()
        return pid

    def remove_profile(self, profile_id: str):
        if profile_id == "default":
            return
        self.data.get("profiles", {}).pop(profile_id, None)
        if self.data.get("active_profile") == profile_id:
            self.data["active_profile"] = "default"
        self.save()

    # ── Activity Log ─────────────────────────────────────────────────────
    def log_activity(self, action: str, details: str):
        log = self.data.setdefault("activity_log", [])
        log.insert(0, {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": action, "details": details})
        # Keep the last 100 records
        self.data["activity_log"] = log[:100]
        self.save()

