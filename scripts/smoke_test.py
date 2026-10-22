"""Smoke test: connect to a running Rabi server with the official MCP client,
print the negotiated protocol version, list tools and call `ping`."""

import asyncio
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = sys.argv[1] if len(sys.argv) > 1 else f"http://127.0.0.1:{os.getenv('RABI_PORT', '8000')}/mcp"


async def main() -> None:
    async with streamable_http_client(URL) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("protocolVersion:", init.protocol_version)
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool("ping", {})
            print("ping:", result.content[0].text)


asyncio.run(main())
