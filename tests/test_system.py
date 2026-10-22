from types import SimpleNamespace

from rabi.tools import system


def test_memory_pressure_unknown_off_macos(monkeypatch):
    monkeypatch.setattr(system, "is_macos", lambda: False)
    assert system.memory_pressure_level() == "unknown"


def test_memory_pressure_maps_sysctl_levels(monkeypatch):
    monkeypatch.setattr(system, "is_macos", lambda: True)
    for raw, label in [("1\n", "normal"), ("2\n", "warning"), ("4\n", "critical"), ("x", "unknown")]:
        monkeypatch.setattr(system, "run", lambda cmd, raw=raw: raw)
        assert system.memory_pressure_level() == label


def test_system_health_shape(monkeypatch):
    gb = 1024**3
    monkeypatch.setattr(system.psutil, "virtual_memory", lambda: SimpleNamespace(total=8 * gb, available=2 * gb, percent=75.0))
    monkeypatch.setattr(system.psutil, "swap_memory", lambda: SimpleNamespace(used=3 * gb, total=4 * gb))
    monkeypatch.setattr(system.psutil, "cpu_percent", lambda interval: 50.0)
    monkeypatch.setattr(system.psutil, "cpu_count", lambda: 8)
    monkeypatch.setattr(system.os, "getloadavg", lambda: (9.0, 4.0, 2.0))
    monkeypatch.setattr(system, "memory_pressure_level", lambda: "warning")
    h = system.system_health()
    assert h["memory_used_gb"] == 6.0
    assert h["swap_used_gb"] == 3.0
    assert h["cpu_overloaded"] is True
    assert h["memory_pressure"] == "warning"
