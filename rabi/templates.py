"""Plain-text fallbacks used when Bedrock is unavailable. Short and spoken-style."""


def _slow_mac(d: dict) -> str:
    health, apps, disk = d.get("system_health", {}), d.get("heavy_apps", {}), d.get("disk_space", {})
    top = (apps.get("top_by_memory") or [{}])[0]
    parts = []
    if top.get("app"):
        parts.append(f"{top['app']} is using the most memory, about {top['memory_mb'] / 1024:.1f} gigabytes.")
    pressure = health.get("memory_pressure", "unknown")
    if pressure in ("warning", "critical"):
        parts.append(f"Memory pressure is {pressure}, so your Mac is swapping to disk.")
    elif health.get("cpu_overloaded"):
        parts.append("Your processor is busier than it can keep up with.")
    if disk.get("low_space"):
        parts.append(f"You also only have {disk['free_gb']} gigabytes free on disk.")
    if top.get("app"):
        parts.append(f"Closing {top['app']} if you're not using it would help most.")
    return " ".join(parts) or "Your Mac looks healthy right now."


def _icloud(d: dict) -> str:
    n = d.get("projects_with_offloaded_files", 0)
    if not n:
        return "None of your projects have files stuck in iCloud. Keeping code in your dev folder keeps it that way."
    worst = d["projects"][0]
    return (f"{n} of your projects have files offloaded to iCloud. {worst['project']} is about "
            f"{worst['percent_offloaded']:.0f} percent offloaded, which makes imports painfully slow. "
            "Move it into your dev folder and recreate its virtual environment.")


def _unpushed(d: dict) -> str:
    risky = d.get("repos_with_unsaved_work", [])
    if not risky:
        return "Everything in your projects is committed and pushed. Nice."
    names = ", ".join(r["repo"].rsplit("/", 1)[-1] for r in risky[:3])
    return f"{len(risky)} repos have work that only lives on this Mac, including {names}. Commit and push before you close anything."


TEMPLATES = {"slow_mac": _slow_mac, "icloud_stuck_projects": _icloud, "unpushed_work": _unpushed}


def template_explanation(topic: str, data: dict) -> str:
    fn = TEMPLATES.get(topic)
    if fn:
        try:
            return fn(data)
        except (KeyError, TypeError, IndexError):
            pass
    return "I checked your Mac and have the details, but couldn't summarise them nicely just now."
