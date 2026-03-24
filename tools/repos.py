import json
import httpx


async def get_repo(client: httpx.AsyncClient, name: str) -> str:
    """Get full details for a specific repo by name, including taxonomy, skills, categories, and commits."""
    try:
        response = await client.get(f"/repos/{name}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Repo '{name}' not found."})
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def find_similar_repos(client: httpx.AsyncClient, repo_name: str, limit: int = 5) -> str:
    """Find repos similar to a given repo by using its readme summary as a semantic search query."""
    try:
        # First, get the repo to retrieve its readme_summary
        repo_response = await client.get(f"/repos/{repo_name}")
        repo_response.raise_for_status()
        repo_data = repo_response.json()

        readme_summary = repo_data.get("readme_summary") or repo_data.get("description") or repo_name
        if not readme_summary:
            return json.dumps({"error": f"No summary available for repo '{repo_name}' to find similar repos."})

        # Use the summary as a semantic search query
        search_response = await client.get("/search/semantic", params={"q": readme_summary, "limit": limit + 1})
        search_response.raise_for_status()
        results = search_response.json()

        # Filter out the source repo from results
        if isinstance(results, list):
            filtered = [r for r in results if r.get("name") != repo_name and r.get("full_name") != repo_name]
            filtered = filtered[:limit]
        elif isinstance(results, dict) and "results" in results:
            filtered_list = [r for r in results["results"] if r.get("name") != repo_name and r.get("full_name") != repo_name]
            filtered = {"results": filtered_list[:limit], "query_repo": repo_name}
        else:
            filtered = results

        return json.dumps(filtered, indent=2)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Repo '{repo_name}' not found."})
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
