"""system_health: a quick snapshot of CPU, memory, memory pressure and swap."""

import os

import psutil

from rabi.tools._macos import is_macos, run

# kern.memorystatus_vm_pressure_level values used by macOS (1/2/4).
_PRESSURE_LEVELS = {1: "normal", 2: "warning", 4: "critical"}


def _gb(n: int) -> float:
    return round(n / 1024**3, 1)


def memory_pressure_level() -> str:
    """Return macOS memory pressure as normal/warning/critical, or 'unknown'.

    Memory pressure is a better 'is my Mac struggling' signal than percent used,
    because macOS deliberately fills RAM with cache.
    """
    if not is_macos():
        return "unknown"
    out = run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
    try:
        return _PRESSURE_LEVELS.get(int(out.strip()), "unknown") if out else "unknown"
    except ValueError:
        return "unknown"


def system_health() -> dict:
    """CPU load, memory used, memory pressure level and swap usage."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load1, load5, _ = os.getloadavg()
    cores = psutil.cpu_count() or 1
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "load_average_1m": round(load1, 2),
        "load_average_5m": round(load5, 2),
        "cpu_cores": cores,
        # Load above the core count means work is queueing up.
        "cpu_overloaded": load1 > cores,
        "memory_total_gb": _gb(vm.total),
        "memory_used_gb": _gb(vm.total - vm.available),
        "memory_percent": vm.percent,
        "memory_pressure": memory_pressure_level(),
        "swap_used_gb": _gb(swap.used),
        "swap_total_gb": _gb(swap.total),
    }
