"""Shared test fixtures and helpers for the reporium-mcp tool tests.

All tests in this suite MOCK the Reporium API. No network calls are made and
no real tokens or URLs are used. The helpers here build httpx-shaped mock
responses and mock AsyncClients so each tool module can be exercised against
deterministic, in-memory data.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


def make_response(
    json_body=None,
    status_code: int = 200,
    text: str = "",
    raise_for_status_error: Exception | None = None,
):
    """Build a MagicMock that quacks like an httpx.Response.

    - ``.json()`` returns ``json_body``.
    - ``.status_code`` / ``.text`` are set as given.
    - ``.raise_for_status()`` raises ``raise_for_status_error`` if provided,
      otherwise is a no-op (mirroring a 2xx response).
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_body

    if raise_for_status_error is not None:
        response.raise_for_status = MagicMock(side_effect=raise_for_status_error)
    else:
        response.raise_for_status = MagicMock()

    return response


def http_status_error(status_code: int, text: str = ""):
    """Construct a real httpx.HTTPStatusError carrying a response with the
    given status code and body text, exactly as ``raise_for_status`` would.
    """
    request = httpx.Request("GET", "https://mock.invalid/endpoint")
    response = httpx.Response(status_code, text=text, request=request)
    return httpx.HTTPStatusError(
        f"{status_code} error", request=request, response=response
    )


def make_client(get=None, post=None):
    """Return an AsyncMock httpx.AsyncClient.

    ``get`` / ``post`` may be a single response, a list of responses (used as a
    side_effect sequence), or an Exception (raised on call).
    """
    client = AsyncMock(spec=httpx.AsyncClient)

    def configure(method_mock, behaviour):
        if behaviour is None:
            return
        if isinstance(behaviour, Exception):
            method_mock.side_effect = behaviour
        elif isinstance(behaviour, list):
            method_mock.side_effect = behaviour
        else:
            method_mock.return_value = behaviour

    configure(client.get, get)
    configure(client.post, post)
    return client


def loads(result: str):
    """Tool functions all return a JSON string; parse it back for assertions."""
    return json.loads(result)


@pytest.fixture
def make_response_factory():
    return make_response
