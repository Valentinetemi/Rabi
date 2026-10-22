"""Small helpers for running macOS commands safely."""

import platform
import subprocess


def is_macos() -> bool:
    return platform.system() == "Darwin"


def run(cmd: list[str], timeout: float = 5.0) -> str | None:
    """Run a command and return stdout, or None if it fails.

    Never raises: a missing command or a slow call should degrade the answer,
    not crash a voice conversation.
    """
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return None
