"""Ask Rabi a question out loud: it picks a tool, then speaks the answer with macOS `say`.

A stand-in for the Alexa+ voice layer so you can demo Rabi on your Mac alone.
Usage:  python scripts/talk.py "why is my mac slow"
        python scripts/talk.py            # then type your question
"""

import asyncio
import json
import subprocess
import sys

from call_tool import URL, ClientSession, httpx2, os, streamable_http_client

# Simple keyword routing; Alexa+ does real intent matching, this just picks a tool for the demo.
ROUTES = [
    (("slow", "lag", "struggl"), "why_is_my_mac_slow"),
    (("journey", "lost", "sad", "record", "encourag"), "my_journey"),
    (("disk", "storage", "space"), "disk_space"),
    (("memory", "ram", "health"), "system_health"),
    (("apps", "heavy"), "heavy_apps"),
    (("push", "commit", "unpushed"), "unpushed_work"),
]


def pick_tool(question: str) -> str:
    q = question.lower()
    for words, tool in ROUTES:
        if any(w in q for w in words):
            return tool
    return "why_is_my_mac_slow"


def to_speech(raw: str) -> str:
    # Spoken tools return {"text": ...}; for raw-data tools, read a short JSON summary.
    try:
        data = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(data, dict) and "text" in data:
        return data["text"]
    return "Here is what I found. " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in list(data.items())[:5]) if isinstance(data, dict) else raw


async def ask(question: str) -> None:
    tool = pick_tool(question)
    token = os.getenv("RABI_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=120) as http, streamable_http_client(URL, http_client=http) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            result = await session.call_tool(tool, {})
    raw = "".join(getattr(p, "text", "") for p in result.content)
    speech = to_speech(raw)
    print(f"[Rabi -> {tool}]\n{speech}")
    subprocess.run(["say", speech], check=False)  # macOS text-to-speech


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or input("Ask Rabi: ")
    asyncio.run(ask(q))
