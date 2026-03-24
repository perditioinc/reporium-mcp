import json
import httpx


async def ask_portfolio(client: httpx.AsyncClient, question: str) -> str:
    """Ask a natural language question about the repo library portfolio. Returns an AI-generated answer.
    Example questions: 'What are our strongest areas?', 'Do we have anything for real-time fraud detection?'"""
    try:
        response = await client.post("/intelligence/ask", json={"question": question})
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_portfolio_gaps(client: httpx.AsyncClient) -> str:
    """Get a gap analysis of the repo library showing which skill/taxonomy areas have insufficient coverage."""
    try:
        response = await client.get("/gaps")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_ai_trends(client: httpx.AsyncClient) -> str:
    """Get trending AI topics represented in the library, sorted by repo count and trending score."""
    try:
        response = await client.get("/taxonomy/ai_trend")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_portfolio_insights(client: httpx.AsyncClient) -> str:
    """Get proactive portfolio intelligence signals from the live intelligence feed."""
    try:
        response = await client.get("/intelligence/portfolio-insights")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_cross_dimension_stats(
    client: httpx.AsyncClient,
    dim1: str,
    dim2: str,
    limit: int = 10,
) -> str:
    """Get cross-dimension portfolio counts for a pair of taxonomy dimensions."""
    try:
        response = await client.get(
            "/analytics/cross-dimension",
            params={"dim1": dim1, "dim2": dim2, "limit": limit},
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
