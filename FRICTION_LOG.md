# Friction log

Things in the MCP SDK, Amazon Bedrock or AWS setup that didn't work the way I expected while building Rabi.

## Template

```
### <short title>
- Date:
- Area: MCP SDK | Bedrock | AWS setup | Tooling
- Task: what I was trying to do
- Steps: what I did
- Expected:
- Actual:
- Severity: low | medium | high | blocker
- Workaround:
- Suggestion:
```

---

### `FastMCP` import fails on the current MCP Python SDK
- Date: 2026-10-22
- Area: MCP SDK
- Task: Create a minimal Streamable HTTP server with one tool.
- Steps: `pip install mcp` (got 2.3.0), followed the common pattern `from mcp.server.fastmcp import FastMCP`.
- Expected: Import works, as in most tutorials and examples.
- Actual: `ModuleNotFoundError`. In 2.x, `FastMCP` was renamed to `mcp.server.mcpserver.MCPServer`. The error message does point to the migration guide, which helped.
- Severity: medium (every v1 tutorial breaks)
- Workaround: `from mcp.server.mcpserver import MCPServer`; `mcp.run("streamable-http", ...)` / `mcp.streamable_http_app(...)`.
- Suggestion: Put the v1→v2 rename at the top of the README quickstart and on PyPI.

### Hard to confirm which protocol version the SDK negotiates
- Date: 2026-10-22
- Area: MCP SDK
- Task: Prove the server uses spec 2025-11-25 or later (hackathon requirement) and pin the right SDK version.
- Steps: Looked for `mcp.shared.version.LATEST_PROTOCOL_VERSION` (where it lived in 1.x).
- Expected: One constant naming the version the server speaks.
- Actual: The module is gone; versions now live in the separate `mcp-types` package (`mcp_types.version`), split into `HANDSHAKE_PROTOCOL_VERSIONS` (up to 2025-11-25) and `MODERN_PROTOCOL_VERSIONS` (2026-07-28). `LATEST_PROTOCOL_VERSION` is 2026-07-28 but `initialize` negotiates 2025-11-25.
- Severity: low
- Workaround: Pinned `mcp==2.3.0` and `mcp-types==2.3.0`, then verified with a real client handshake (`scripts/smoke_test.py`, `tests/test_server_e2e.py`) that `protocolVersion` is `2025-11-25`.
- Suggestion: Document "which spec versions does this release speak" in each release note, and expose a single `server.supported_versions()`.

### Tunnel requests rejected by DNS-rebinding protection
- Date: 2026-10-22
- Area: MCP SDK
- Task: Expose the localhost server to Alexa+ through ngrok.
- Steps: Ran the server on 127.0.0.1, sent a request with a different `Host` header (what a tunnel forwards).
- Expected: Request reaches the server (auth is our job).
- Actual: The SDK auto-enables DNS-rebinding protection for localhost binds and only allows `127.0.0.1:*`, `localhost:*`, `[::1]:*`. A foreign Host gets HTTP 400 before any of our code runs.
- Severity: medium (silent-looking failure from the Alexa side)
- Workaround: Pass `TransportSecuritySettings(allowed_hosts=[..., "<tunnel host>"])`; Rabi reads these from `RABI_PUBLIC_HOSTS`.
- Suggestion: Log a clear warning naming the rejected Host and the setting to change.

### MCP Inspector v2 needs Node 22.19+
- Date: 2026-10-22
- Area: Tooling
- Task: Test the server with `npx @modelcontextprotocol/inspector`.
- Steps: Build machine had Node 20.19.
- Expected: Inspector runs.
- Actual: Inspector v2 requires Node `>=22.19.0`. Its web UI also changed from v1 (the old left-pane Transport dropdown tutorials describe), and it can pre-connect with `--transport http --server-url ...`.
- Severity: low
- Workaround: Verified with the Python SDK client instead; documented Node 22 requirement and v2 flags in the README.
- Suggestion: Print a friendly "Node too old" message from the `npx` launcher.

### Bedrock (to fill in when testing on the Mac)
- Area: Bedrock / AWS setup
- Notes: Converse call is unit-tested with a mocked client only. Record here anything about model access, inference profile IDs (`us.` prefix), credentials or region when running it for real.
