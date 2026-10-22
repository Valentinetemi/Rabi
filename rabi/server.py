"""Rabi MCP server: Mac diagnostics and encouragement for developers, via Alexa+.

Run with:  python -m rabi.server
Serves MCP over Streamable HTTP at http://<RABI_HOST>:<RABI_PORT>/mcp
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from rabi.auth import BearerAuthMiddleware, auth_required

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
AUTH_TOKEN = os.getenv("RABI_AUTH_TOKEN") or None
# Public hostnames that forward to us, e.g. "abc123.ngrok-free.app" (comma separated).
PUBLIC_HOSTS = [h.strip() for h in os.getenv("RABI_PUBLIC_HOSTS", "").split(",") if h.strip()]

# Instructions are sent to the client (Alexa+) at connect time; they steer how
# the assistant uses the tools, especially the confirmation step in close_app.
INSTRUCTIONS = (
    "Rabi helps a developer understand why their Mac is slow and encourages them after setbacks. "
    "For 'why is my Mac slow' use why_is_my_mac_slow and read its text aloud. "
    "Before closing any app, call close_app without a token, ask the user to confirm out loud, "
    "and only then call it again with the confirm_token. Never guess a token. "
    "When the user says they lost, didn't win or got rejected, use my_journey."
)

mcp = MCPServer("rabi", title="Rabi", version="0.1.0", instructions=INSTRUCTIONS)


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


def build_app():
    """Create the Streamable HTTP ASGI app, adding auth and host checks as needed."""
    # The SDK blocks unknown Host headers (DNS-rebinding protection). A tunnel like
    # ngrok sends its own hostname, so we must list it explicitly to allow it.
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *PUBLIC_HOSTS],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
                         *(f"https://{h}" for h in PUBLIC_HOSTS)],
    )
    app = mcp.streamable_http_app(streamable_http_path="/mcp", transport_security=security, host=HOST)
    if auth_required(HOST, AUTH_TOKEN, PUBLIC_HOSTS):
        if not AUTH_TOKEN:
            # Refuse to run exposed without a secret rather than silently being open.
            raise SystemExit("RABI_AUTH_TOKEN must be set when Rabi is exposed beyond localhost.")
        app = BearerAuthMiddleware(app, AUTH_TOKEN)
    return app


def main() -> None:
    import uvicorn

    # Streamable HTTP is the transport required by the Alexa+ track (spec 2025-11-25).
    uvicorn.run(build_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
