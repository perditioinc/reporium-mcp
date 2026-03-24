import json
import httpx


async def search_repos(client: httpx.AsyncClient, query: str, limit: int = 10) -> str:
    """Search the Reporium library using keyword/text matching."""
    try:
        response = await client.get("/search", params={"q": query, "limit": limit})
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def search_repos_semantic(client: httpx.AsyncClient, query: str, limit: int = 10) -> str:
    """Search the Reporium library using semantic/vector similarity. Returns results with similarity scores."""
    try:
        response = await client.get("/search/semantic", params={"q": query, "limit": limit})
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
