"""Shared pytest fixtures and mock helpers for the Reporium MCP tool tests.

All tests in this suite MOCK the Reporium API. No network calls are made.
The helpers below build httpx-shaped mock objects so the tool functions
exercise their real code paths (request building, status handling, JSON
shaping, error formatting) without a live backend.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


def make_response(json_data=None, status_code: int = 200, text: str = "") -> MagicMock:
    """Build a MagicMock that quacks like an httpx.Response.

    raise_for_status() raises httpx.HTTPStatusError for >= 400, mirroring
    httpx's real behaviour, so error-handling branches are exercised.
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text or (json.dumps(json_data) if json_data is not None else "")
    response.json = MagicMock(return_value=json_data)

    request = httpx.Request("GET", "http://test.local/endpoint")
    response.request = request

    def _raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {status_code}", request=request, response=response
            )

    response.raise_for_status = MagicMock(side_effect=_raise_for_status)
    return response


def make_client(get_return=None, post_return=None,
                get_side_effect=None, post_side_effect=None) -> AsyncMock:
    """Build an AsyncMock httpx.AsyncClient with get/post stubbed.

    Pass *_return to set a fixed return value, or *_side_effect to raise an
    exception (e.g. httpx.TimeoutException) or sequence multiple responses.
    """
    client = AsyncMock(spec=httpx.AsyncClient)
    if get_side_effect is not None:
        client.get = AsyncMock(side_effect=get_side_effect)
    else:
        client.get = AsyncMock(return_value=get_return)
    if post_side_effect is not None:
        client.post = AsyncMock(side_effect=post_side_effect)
    else:
        client.post = AsyncMock(return_value=post_return)
    return client


@pytest.fixture
def response_factory():
    return make_response


@pytest.fixture
def client_factory():
    return make_client
