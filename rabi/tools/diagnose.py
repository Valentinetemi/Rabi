"""Spoken-answer tools: run checks, then explain them via Bedrock (or a template)."""

from rabi.explain import explain
from rabi.tools.apps import heavy_apps
from rabi.tools.disk import disk_space
from rabi.tools.git_work import unpushed_work
from rabi.tools.icloud import icloud_stuck_projects
from rabi.tools.system import system_health


def why_is_my_mac_slow() -> dict:
    """Answer 'why is my Mac slow?': checks memory, CPU, heavy apps and disk, then explains in a few spoken sentences."""
    data = {"system_health": system_health(), "heavy_apps": heavy_apps(limit=3), "disk_space": disk_space()}
    return {**explain("slow_mac", data), "data": data}


# Checks that `explain_check` may run. Keeps the tool from calling arbitrary code.
_CHECKS = {
    "icloud_stuck_projects": icloud_stuck_projects,
    "unpushed_work": unpushed_work,
    "system_health": system_health,
    "heavy_apps": heavy_apps,
    "disk_space": disk_space,
}


def explain_check(check: str) -> dict:
    """Run one check (icloud_stuck_projects, unpushed_work, system_health, heavy_apps, disk_space) and explain it aloud."""
    fn = _CHECKS.get(check)
    if fn is None:
        return {"text": f"I don't have a check called {check}.", "source": "template", "available": list(_CHECKS)}
    data = fn()
    return {**explain(check, data), "data": data}
