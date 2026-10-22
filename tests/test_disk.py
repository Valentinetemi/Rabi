from types import SimpleNamespace

from rabi.tools import disk


def test_disk_space_flags_low_space(monkeypatch):
    gb = 1024**3
    monkeypatch.setattr(disk, "main_disk_path", lambda: "/")
    monkeypatch.setattr(disk.psutil, "disk_usage", lambda p: SimpleNamespace(total=256 * gb, used=250 * gb, free=6 * gb, percent=97.7))
    d = disk.disk_space()
    assert d["free_gb"] == 6.0 and d["low_space"] is True


def test_prefers_mac_data_volume(monkeypatch):
    monkeypatch.setattr(disk.os.path, "isdir", lambda p: p == "/System/Volumes/Data")
    assert disk.main_disk_path() == "/System/Volumes/Data"
