from types import SimpleNamespace

from rabi.tools import apps


def test_app_name_uses_outermost_bundle():
    exe = "/Applications/Google Chrome.app/Contents/Frameworks/X.framework/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/x"
    assert apps.app_name_for(exe, "Google Chrome Helper (Renderer)") == "Google Chrome"


def test_app_name_falls_back_to_process_name():
    assert apps.app_name_for("/usr/bin/python3", "python3") == "python3"
    assert apps.app_name_for(None, "kernel_task") == "kernel_task"


class FakeProc:
    def __init__(self, name, exe, rss, cpu):
        self.info = {"name": name, "exe": exe, "memory_info": SimpleNamespace(rss=rss)}
        self._cpu = cpu

    def cpu_percent(self, _):
        return self._cpu


def test_heavy_apps_groups_and_sorts(monkeypatch):
    mb = 1024**2
    procs = [
        FakeProc("Xcode", "/Applications/Xcode.app/Contents/MacOS/Xcode", 3000 * mb, 20.0),
        FakeProc("Simulator", "/Applications/Xcode.app/Contents/Developer/Applications/Simulator.app/x", 1000 * mb, 40.0),
        FakeProc("python3", "/usr/bin/python3", 500 * mb, 90.0),
    ]
    monkeypatch.setattr(apps.psutil, "process_iter", lambda attrs: procs)
    monkeypatch.setattr(apps.time, "sleep", lambda s: None)
    out = apps.heavy_apps(limit=2)
    assert out["top_by_memory"][0] == {"app": "Xcode", "memory_mb": 4000, "cpu_percent": 60.0, "processes": 2}
    assert out["top_by_cpu"][0]["app"] == "python3"
