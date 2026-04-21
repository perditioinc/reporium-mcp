import json
import httpx

VALID_DIMENSIONS = [
    "skill_area",
    "industry",
    "use_case",
    "modality",
    "ai_trend",
    "deployment_context",
    "tags",
    "categories",
]


async def list_taxonomy_dimensions(client: httpx.AsyncClient) -> str:
    """List all active taxonomy dimensions with their repo counts. Use this to understand how the library is categorized."""
    try:
        response = await client.get("/taxonomy/dimensions")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def list_taxonomy_values(client: httpx.AsyncClient, dimension: str) -> str:
    """List all values for a taxonomy dimension, sorted by repo count.
    Valid dimensions: skill_area, industry, use_case, modality, ai_trend, deployment_context, tags, categories."""
    if dimension not in VALID_DIMENSIONS:
        return json.dumps({
            "error": f"Invalid dimension '{dimension}'. Valid dimensions are: {', '.join(VALID_DIMENSIONS)}"
        })
    try:
        response = await client.get(f"/taxonomy/{dimension}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_repos_by_taxonomy(client: httpx.AsyncClient, dimension: str, value: str, limit: int = 20) -> str:
    """Get repos matching a specific taxonomy dimension and value (e.g., skill_area=nlp, industry=healthcare)."""
    if dimension not in VALID_DIMENSIONS:
        return json.dumps({
            "error": f"Invalid dimension '{dimension}'. Valid dimensions are: {', '.join(VALID_DIMENSIONS)}"
        })
    try:
        # Try the dedicated endpoint first
        response = await client.get(f"/taxonomy/{dimension}/{value}/repos", params={"limit": limit})
        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)

        # Fall back to filtering from the full library
        if response.status_code == 404:
            full_response = await client.get("/library/full")
            full_response.raise_for_status()
            library = full_response.json()

            repos = library if isinstance(library, list) else library.get("repos", [])
            matched = [
                r for r in repos
                if value.lower() in [
                    str(v).lower() for v in (
                        r.get("taxonomy", {}).get(dimension, [])
                        if isinstance(r.get("taxonomy", {}).get(dimension), list)
                        else [r.get("taxonomy", {}).get(dimension, "")]
                    )
                ]
            ]
            return json.dumps(matched[:limit], indent=2)

        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
