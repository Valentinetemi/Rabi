"""disk_space: free and used space on the main disk."""

import os

import psutil

# On modern macOS "/" is a sealed read-only system volume; user files live on the
# Data volume. Both share one APFS container, but Data reports real usage best.
_MAC_DATA_VOLUME = "/System/Volumes/Data"


def main_disk_path() -> str:
    return _MAC_DATA_VOLUME if os.path.isdir(_MAC_DATA_VOLUME) else "/"


def disk_space() -> dict:
    """Free and used space on the main disk, plus a low-space warning."""
    path = main_disk_path()
    u = psutil.disk_usage(path)
    free_gb = round(u.free / 1024**3, 1)
    return {
        "path": path,
        "total_gb": round(u.total / 1024**3, 1),
        "used_gb": round(u.used / 1024**3, 1),
        "free_gb": free_gb,
        "percent_used": u.percent,
        # Under ~10 GB macOS struggles to swap and update; worth flagging.
        "low_space": free_gb < 10,
    }
