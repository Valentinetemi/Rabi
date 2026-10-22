"""Call one Rabi tool through a real MCP client and print the result.

Usage:  python scripts/call_tool.py system_health
        python scripts/call_tool.py close_app '{"app_name": "Simulator"}'
"""

import asyncio
import json
import os
import sys

import httpx2
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()
URL = os.getenv("RABI_URL", f"http://127.0.0.1:{os.getenv('RABI_PORT', '8000')}/mcp")


async def main(tool: str, args: dict) -> None:
    token = os.getenv("RABI_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=120) as http, streamable_http_client(URL, http_client=http) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            for part in result.content:
                print(getattr(part, "text", part))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
