"""Shared pytest fixtures and helpers for the reporium-mcp test suite.

These tests are fully offline: every reporium-api call is mocked. No test in
this suite performs a live HTTP request. The conftest adds the repo root to
sys.path so `import mcp_server` and `from tools.* import ...` resolve without
relying on an externally set PYTHONPATH.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

# Make the repo root importable (mcp_server.py + tools/ package) regardless of
# how pytest is invoked.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def make_response(json_body=None, status_code: int = 200, text: str = ""):
    """Build a MagicMock that behaves like an httpx.Response for our tools.

    The tool functions only ever touch: .json(), .raise_for_status(),
    .status_code, and (on error) .text. We model exactly those.
    """
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_body if json_body is not None else {}

    if status_code >= 400:
        request = httpx.Request("GET", "http://mock.local")
        # raise_for_status raises like the real httpx does for >=400.
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=request, response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def mock_client():
    """An AsyncMock standing in for httpx.AsyncClient.

    Tests set mock_client.get.return_value / .post.return_value (or
    .side_effect) to whatever make_response(...) produces.
    """
    client = AsyncMock(spec=httpx.AsyncClient)
    return client
