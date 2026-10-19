import os

import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "RAG-ProjectB-research-agent/0.1 (educational project)"


def web_search(query: str) -> dict:
    """Search the open web (Wikipedia) for a topic.

    Returns {"results": [{"title": str, "url": str, "snippet": str}]} on success,
    or {"error": str} if something goes wrong.
    """
    if not query or not query.strip():
        return {"error": "query must be a non-empty string"}

    timeout = float(os.environ.get("TOOL_TIMEOUT_SECONDS", "20"))
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": 3,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "exsentences": 2,
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
    }

    try:
        response = requests.get(
            WIKIPEDIA_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
        )
        response.raise_for_status()
    except requests.Timeout:
        return {"error": f"Web search timed out after {timeout:g}s"}
    except requests.ConnectionError:
        return {"error": "Web search is unreachable - check your internet connection"}
    except requests.HTTPError:
        return {"error": f"Web search returned HTTP {response.status_code}"}

    try:
        pages = response.json().get("query", {}).get("pages", [])
    except (ValueError, AttributeError):
        return {"error": "Web search returned an unexpected response"}

    results = [
        {"title": page.get("title", ""), "url": page.get("fullurl", ""), "snippet": page.get("extract", "")}
        for page in sorted(pages, key=lambda p: p.get("index", 0))
    ]
    return {"results": results}
