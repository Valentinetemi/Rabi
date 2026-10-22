"""End-to-end: start the real server and talk to it with the official MCP client."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time

import httpx2
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

EXPECTED_TOOLS = {
    "ping", "system_health", "heavy_apps", "disk_space", "icloud_stuck_projects",
    "unpushed_work", "why_is_my_mac_slow", "explain_check", "my_journey", "close_app",
}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    port = free_port()
    env = {**os.environ, "RABI_PORT": str(port), "RABI_AUTH_TOKEN": "e2e-token", "BEDROCK_MODEL_ID": ""}
    proc = subprocess.Popen([sys.executable, "-m", "rabi.server"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/mcp"
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()
    proc.wait(5)


async def session_run(url, token):
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30) as http:
        async with streamable_http_client(url, http_client=http) as streams:
            async with ClientSession(streams[0], streams[1]) as s:
                init = await s.initialize()
                tools = await s.list_tools()
                ping = await s.call_tool("ping", {})
                refused = await s.call_tool("close_app", {"app_name": "Finder"})
                return init, tools, ping, refused


def test_handshake_tools_and_calls(server):
    init, tools, ping, refused = asyncio.run(session_run(server, "e2e-token"))
    assert init.protocol_version == "2025-11-25"
    assert init.server_info.name == "rabi"
    assert "confirm" in (init.instructions or "")
    assert {t.name for t in tools.tools} == EXPECTED_TOOLS
    assert json.loads(ping.content[0].text)["status"] == "ok"
    assert json.loads(refused.content[0].text)["status"] == "refused"


def test_rejects_missing_token(server):
    r = httpx2.post(server, json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert r.status_code == 401
