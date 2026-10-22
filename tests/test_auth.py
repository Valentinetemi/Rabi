import asyncio

import pytest

from rabi.auth import BearerAuthMiddleware, auth_required


def test_auth_rules():
    assert auth_required("127.0.0.1", None, []) is False
    assert auth_required("127.0.0.1", "t", []) is True
    assert auth_required("0.0.0.0", None, []) is True
    assert auth_required("127.0.0.1", None, ["x.ngrok-free.app"]) is True


async def ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def call(headers):
    sent = []

    async def send(msg):
        sent.append(msg)

    scope = {"type": "http", "headers": headers}
    asyncio.run(BearerAuthMiddleware(ok_app, "s3cret")(scope, None, send))
    return sent[0]["status"]


@pytest.mark.parametrize("headers,status", [
    ([], 401),
    ([(b"authorization", b"Bearer wrong")], 401),
    ([(b"authorization", b"s3cret")], 401),
    ([(b"authorization", b"Bearer s3cret")], 200),
])
def test_middleware(headers, status):
    assert call(headers) == status


def test_lifespan_passes_through():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(BearerAuthMiddleware(app, "t")({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]
