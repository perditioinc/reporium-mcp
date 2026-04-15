"""Test the intelligence client paths."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx
from tools.intelligence import ask_portfolio, get_portfolio_insights


@pytest.mark.asyncio
async def test_ask_portfolio_calls_correct_path():
    """Test that ask_portfolio calls /ask, not /intelligence/ask."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {"answer": "test answer"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response

    result = await ask_portfolio(mock_client, "test question")

    # Verify the correct path was called
    mock_client.post.assert_called_once_with("/ask", json={"question": "test question"})
    assert "test answer" in result


@pytest.mark.asyncio
async def test_get_portfolio_insights_calls_correct_path():
    """Test that get_portfolio_insights calls /insights, not /intelligence/portfolio-insights."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {"insights": ["insight1", "insight2"]}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    result = await get_portfolio_insights(mock_client)

    # Verify the correct path was called
    mock_client.get.assert_called_once_with("/insights")
    assert "insight1" in result
