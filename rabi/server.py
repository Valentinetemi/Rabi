"""Rabi MCP server (step 1: skeleton with a single `ping` tool).

Run with:  python -m rabi.server
Serves MCP over Streamable HTTP at http://<RABI_HOST>:<RABI_PORT>/mcp
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

from rabi.tools.apps import heavy_apps
from rabi.tools.close_app import close_app
from rabi.tools.diagnose import explain_check, why_is_my_mac_slow
from rabi.tools.disk import disk_space
from rabi.tools.git_work import unpushed_work
from rabi.tools.icloud import icloud_stuck_projects
from rabi.tools.journey import my_journey
from rabi.tools.system import system_health

# Load settings from .env so secrets and ports never live in code.
load_dotenv()

# Default to localhost: the server can inspect (and later close apps on) the Mac,
# so it must not be reachable from the network unless we deliberately expose it.
HOST = os.getenv("RABI_HOST", "127.0.0.1")
PORT = int(os.getenv("RABI_PORT", "8000"))

mcp = MCPServer("rabi")


@mcp.tool()
def ping() -> dict:
    """Check that the Rabi server is alive. Returns status, server name and current UTC time."""
    # A trivial tool lets us prove the full MCP round trip before adding real checks.
    return {
        "status": "ok",
        "server": "rabi",
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# Register diagnosis tools. Docstrings become the tool descriptions Alexa+ sees.
mcp.tool()(system_health)
mcp.tool()(heavy_apps)
mcp.tool()(disk_space)
mcp.tool()(icloud_stuck_projects)
mcp.tool()(unpushed_work)

# Spoken-style answers, explained by Amazon Bedrock (template fallback).
mcp.tool()(why_is_my_mac_slow)
mcp.tool()(explain_check)

# Encouragement grounded in data/journey.json.
mcp.tool()(my_journey)

# The only tool that changes anything; it requires a confirmation round trip.
mcp.tool()(close_app)


def main() -> None:
    # Streamable HTTP is the transport required by the Alexa+ track (spec 2025-11-25).
    mcp.run("streamable-http", host=HOST, port=PORT, streamable_http_path="/mcp")


if __name__ == "__main__":
    main()
