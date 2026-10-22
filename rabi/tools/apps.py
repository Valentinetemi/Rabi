"""heavy_apps: which apps are using the most memory and CPU, grouped by app."""

import time
from collections import defaultdict

import psutil


def app_name_for(exe: str | None, proc_name: str) -> str:
    """Map a process to the app a person would recognise.

    Chrome, Slack, VS Code and Xcode run many helper processes whose executables
    live inside the main bundle, e.g.
    /Applications/Google Chrome.app/Contents/Frameworks/.../Google Chrome Helper.app/...
    The outermost ".app" is the app the user actually opened.
    """
    if exe and ".app/" in exe:
        outer = exe.split(".app/")[0]
        return outer.rsplit("/", 1)[-1]
    return proc_name or "unknown"


def heavy_apps(limit: int = 5) -> dict:
    """Top apps by memory and by CPU, with helper processes grouped under their app."""
    procs = list(psutil.process_iter(["name", "exe", "memory_info"]))
    # cpu_percent needs two samples; prime every process, wait briefly, then read.
    for p in procs:
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(0.5)

    mem = defaultdict(int)
    cpu = defaultdict(float)
    count = defaultdict(int)
    for p in procs:
        try:
            name = app_name_for(p.info.get("exe"), p.info.get("name") or "")
            mi = p.info.get("memory_info")
            mem[name] += mi.rss if mi else 0
            cpu[name] += p.cpu_percent(None)
            count[name] += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue  # processes come and go; skip the ones we can't read

    def row(name: str) -> dict:
        return {
            "app": name,
            "memory_mb": round(mem[name] / 1024**2),
            "cpu_percent": round(cpu[name], 1),
            "processes": count[name],
        }

    by_mem = sorted(mem, key=mem.get, reverse=True)[:limit]
    by_cpu = sorted(cpu, key=cpu.get, reverse=True)[:limit]
    return {"top_by_memory": [row(n) for n in by_mem], "top_by_cpu": [row(n) for n in by_cpu]}
