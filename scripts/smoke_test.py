"""Smoke test: connect to a running Rabi server with the official MCP client,
print the negotiated protocol version, list tools and call `ping`."""

import asyncio
import os
import sys

import httpx2
from dotenv import load_dotenv

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()
URL = sys.argv[1] if len(sys.argv) > 1 else f"http://127.0.0.1:{os.getenv('RABI_PORT', '8000')}/mcp"


async def main() -> None:
    # Send the bearer token if one is configured, same as Alexa+ would.
    token = os.getenv("RABI_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=30) as http, streamable_http_client(URL, http_client=http) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("protocolVersion:", init.protocol_version)
            tools = await session.list_tools()
            print("tools:", sorted(t.name for t in tools.tools))
            result = await session.call_tool("ping", {})
            print("ping:", result.content[0].text)


asyncio.run(main())
