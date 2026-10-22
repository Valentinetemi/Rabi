"""my_journey: encouragement grounded in your real record, after a tough result.

Rules this tool follows:
  - Acknowledge that it stings first; don't rush to fix feelings.
  - Every number comes from data/journey.json. Nothing is invented.
  - Point at the next real deadline, so there's somewhere to put the energy.
  - Sometimes suggest talking to a friend. This is encouragement, not therapy.
"""

import json
import os
import random
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINISHED = {"won", "placed", "finalist", "submitted", "not_selected"}
# How often to suggest reaching out to a friend (roughly 1 in 3).
FRIEND_CHANCE = 0.35


def journey_path() -> Path:
    custom = os.getenv("RABI_JOURNEY_FILE")
    if custom:
        return Path(custom).expanduser()
    real = PROJECT_ROOT / "data" / "journey.json"
    return real if real.exists() else PROJECT_ROOT / "data" / "journey.example.json"


def load_journey(path: Path | None = None) -> dict:
    path = path or journey_path()
    with open(path) as f:
        data = json.load(f)
    data["_source"] = path.name
    return data


def summarise(data: dict, today: date | None = None) -> dict:
    """Pure counting over the file, so every claim in the reply is checkable."""
    today = today or date.today()
    hacks = data.get("hackathons", [])
    upcoming = sorted(
        (d for d in data.get("upcoming_deadlines", []) if date.fromisoformat(d["date"]) >= today),
        key=lambda d: d["date"],
    )
    return {
        "hackathons_entered": len(hacks),
        "projects_shipped": sum(h.get("result") in FINISHED for h in hacks),
        "hackathon_wins": sum(h.get("result") in ("won", "placed") for h in hacks),
        "finalist": sum(h.get("result") == "finalist" for h in hacks),
        "results_pending": sum(h.get("result") == "pending" for h in hacks),
        "other_wins": [w["title"] for w in data.get("wins", [])],
        "notable_projects": [p["name"] for p in data.get("notable_projects", [])],
        "next_deadline": upcoming[0] if upcoming else None,
    }


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def compose(s: dict, what_happened: str | None, suggest_friend: bool, today: date | None = None) -> str:
    today = today or date.today()
    lines = []
    lines.append(f"I'm sorry about {what_happened}. That stings, and it's okay to feel it." if what_happened
                 else "That sounds disappointing, and it's okay to feel it.")
    facts = []
    if s["hackathons_entered"]:
        facts.append(f"you've entered {_plural(s['hackathons_entered'], 'hackathon')} and shipped {_plural(s['projects_shipped'], 'project')}")
    if s["hackathon_wins"]:
        facts.append(f"won or placed in {s['hackathon_wins']}")
    if s["finalist"]:
        facts.append(f"been a finalist {_plural(s['finalist'], 'time')}")
    if facts:
        lines.append("Here's your real record: " + ", ".join(facts) + ".")
    if s["other_wins"]:
        lines.append(f"And this one went your way: {s['other_wins'][-1]}.")
    if s["results_pending"]:
        lines.append(f"{_plural(s['results_pending'], 'result')} {'is' if s['results_pending'] == 1 else 'are'} still pending.")
    nd = s["next_deadline"]
    if nd:
        days = (date.fromisoformat(nd["date"]) - today).days
        when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
        lines.append(f"Next up is {nd['name']}, {when}.")
    if suggest_friend:
        lines.append("It might also help to tell a friend how this one felt.")
    return " ".join(lines)


def my_journey(what_happened: str | None = None) -> dict:
    """Encouragement after a loss or rejection, using only the real numbers in data/journey.json, plus the next deadline."""
    try:
        data = load_journey()
    except (OSError, ValueError) as e:
        return {"text": "I couldn't read your journey file yet. Copy data/journey.example.json to data/journey.json and fill it in.",
                "error": str(e)}
    s = summarise(data)
    return {
        "text": compose(s, what_happened, suggest_friend=random.random() < FRIEND_CHANCE),
        "summary": s,
        "source_file": data["_source"],
    }
