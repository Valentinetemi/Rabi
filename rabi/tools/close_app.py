"""close_app: quit an app, but only after the user confirms.

Two-step flow so a misheard voice command can't close anything:
  1. close_app(app_name="Simulator")            -> describes the action + token
  2. close_app(app_name="Simulator", confirm_token=...) -> actually quits

Quitting uses AppleScript `quit app`, the same as Cmd+Q, so apps can ask to
save unsaved work. We never force-kill.
"""

import secrets
import time

import psutil

from rabi.tools._macos import is_macos, run
from rabi.tools.apps import app_name_for

TOKEN_TTL_SECONDS = 60

# Quitting these would log you out, break the desktop, or do nothing useful.
PROTECTED_APPS = {
    "finder", "windowserver", "loginwindow", "dock", "systemuiserver", "kernel_task",
    "launchd", "controlcenter", "notificationcenter", "spotlight", "coreaudiod",
    "securityd", "mds", "mds_stores", "system settings", "system preferences",
    "rabi", "python", "python3", "terminal", "iterm2",  # don't cut off our own server
}

# token -> (app name, expiry). In memory only: a restart invalidates all tokens.
_pending: dict[str, tuple[str, float]] = {}


def _running_app(name: str) -> tuple[str, int] | None:
    """Find a running app by case-insensitive name; return (real name, process count)."""
    matches: dict[str, int] = {}
    for p in psutil.process_iter(["name", "exe"]):
        try:
            app = app_name_for(p.info.get("exe"), p.info.get("name") or "")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if app.lower() == name.lower():
            matches[app] = matches.get(app, 0) + 1
    if not matches:
        return None
    real = max(matches, key=matches.get)
    return real, matches[real]


def _purge_expired(now: float) -> None:
    for t in [t for t, (_, exp) in _pending.items() if exp < now]:
        del _pending[t]


def close_app(app_name: str, confirm_token: str | None = None) -> dict:
    """Quit an app gracefully. First call returns a confirmation token; call again with it to quit."""
    now = time.time()
    _purge_expired(now)
    name = app_name.strip().removesuffix(".app")

    if name.lower() in PROTECTED_APPS:
        return {"status": "refused", "app": name, "reason": f"{name} is part of macOS or Rabi itself, so I won't close it."}

    if confirm_token is None:
        found = _running_app(name)
        if not found:
            return {"status": "not_running", "app": name}
        real, procs = found
        token = secrets.token_urlsafe(8)
        _pending[token] = (real, now + TOKEN_TTL_SECONDS)
        return {
            "status": "needs_confirmation",
            "app": real,
            "processes": procs,
            "action": f'Quit "{real}" like pressing Cmd+Q. It may ask you to save open work.',
            "confirm_token": token,
            "expires_in_seconds": TOKEN_TTL_SECONDS,
        }

    # Second call: token must exist, be unexpired, and match this app. Single use.
    entry = _pending.pop(confirm_token, None)
    if entry is None:
        return {"status": "invalid_token", "app": name, "reason": "Token is unknown, used, or expired. Ask again to get a new one."}
    real, _ = entry
    if real.lower() != name.lower():
        return {"status": "invalid_token", "app": name, "reason": f"That token was for {real}, not {name}."}

    if not is_macos():
        return {"status": "unsupported", "app": real, "reason": "Closing apps only works on macOS."}
    # Escape quotes so an app name can't break out of the AppleScript string.
    safe = real.replace("\\", "\\\\").replace('"', '\\"')
    out = run(["osascript", "-e", f'quit app "{safe}"'], timeout=15)
    if out is None:
        return {"status": "failed", "app": real, "reason": "macOS didn't accept the quit request. The app may be showing a dialog."}
    return {"status": "quit_requested", "app": real}
