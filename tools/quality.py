import json
import httpx


async def get_quality_signals(client: httpx.AsyncClient, repo_name: str) -> str:
    """
    Get the quality signals for a specific repository.

    Calls GET /repos/{name} and returns the quality_signals dict,
    or an explanatory message if quality signals are not yet computed.
    """
    try:
        response = await client.get(f"/repos/{repo_name}")
        response.raise_for_status()
        data = response.json()
        quality_signals = data.get("quality_signals")
        if quality_signals is None:
            return json.dumps({
                "repo": repo_name,
                "quality_signals": None,
                "message": "Quality signals have not been computed for this repo yet. "
                           "An admin can run POST /admin/quality/compute to generate them.",
            }, indent=2)
        return json.dumps({
            "repo": repo_name,
            "quality_signals": quality_signals,
        }, indent=2)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Repo '{repo_name}' not found."})
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def list_taxonomy_gaps(
    client: httpx.AsyncClient,
    dimension: str | None = None,
    min_severity: str = "medium",
) -> str:
    """
    List taxonomy gaps from GET /gaps/taxonomy, filtered by minimum severity.

    Severity levels (ascending): low < medium < high.
    Only returns items at or above the specified min_severity level.
    Optionally filters by dimension.
    """
    _SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
    min_level = _SEVERITY_ORDER.get(min_severity.lower(), 1)

    try:
        response = await client.get("/gaps/taxonomy")
        response.raise_for_status()
        items = response.json()

        if not isinstance(items, list):
            return json.dumps({"error": "Unexpected response format from /gaps/taxonomy"})

        # Filter by severity
        filtered = [
            item for item in items
            if _SEVERITY_ORDER.get(item.get("severity", "low"), 0) >= min_level
        ]

        # Filter by dimension if specified
        if dimension:
            filtered = [item for item in filtered if item.get("dimension") == dimension]

        return json.dumps({
            "count": len(filtered),
            "min_severity": min_severity,
            "dimension_filter": dimension,
            "gaps": filtered,
        }, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
