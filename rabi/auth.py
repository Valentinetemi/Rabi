"""Bearer-token protection for when Rabi is reachable beyond this Mac.

Rabi can read your process list and quit apps, so anyone who can reach /mcp
must prove they know RABI_AUTH_TOKEN. On plain localhost with no token set,
auth is off so local testing with MCP Inspector stays easy.
"""

import hmac
import json

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def auth_required(host: str, token: str | None, public_hosts: list[str]) -> bool:
    """Auth is required if a token is set, or if the server is exposed at all."""
    return bool(token) or host not in LOCAL_HOSTS or bool(public_hosts)


class BearerAuthMiddleware:
    """Pure ASGI middleware: rejects HTTP requests without the right bearer token.

    Pure ASGI (not Starlette's BaseHTTPMiddleware) so streaming SSE responses
    pass through untouched.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        provided = dict(scope.get("headers", [])).get(b"authorization", b"")
        # compare_digest avoids leaking the token through timing differences.
        if hmac.compare_digest(provided, self.expected):
            return await self.app(scope, receive, send)
        body = json.dumps({"error": "unauthorized", "hint": "Send Authorization: Bearer <RABI_AUTH_TOKEN>"}).encode()
        await send({"type": "http.response.start", "status": 401, "headers": [
            (b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
        await send({"type": "http.response.body", "body": body})
