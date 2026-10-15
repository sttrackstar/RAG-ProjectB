import os 

import requests


def search_knowledge(query: str) -> dict:
    """Ask the AnythingLLM knowledge base a question.
    
    Returns {"answer": str, "sources": [str]} on success,
    or {"error": str} if something goes wrong. """

    if not query or not query.strip():
        return {"error": "Query must be a non-empty string."}

    base_url = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001")
    api_key = os.environ.get("ANYTHINGLLM_API_KEY", "")
    workspace = os.environ.get("ANYTHINGLLM_WORKSPACE", "apprentice-kb")
    timeout = float(os.environ.get("TOOL_TIMEOUT_SECONDS", "20"))

    url = f"{base_url}/api/v1/workspace/{workspace}/chat"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"message": query, "mode" : "query"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout:
        return {"error": f"Knowledge service timed out after {timeout:g}s"}
    except requests.ConnectionError:
        return {"error": "Knowledge service is unreachable - is AnythingLLM running?"}
    except requests.HTTPError:
        if response.status_code in (401, 403):
            return {"error": "Knowledge service rejected the API key"}
        return {"error": f"Knowledge service returned HTTP {response.status_code}"}

    try:
        data = response.json()
    except ValueError:
        return {"error": "Knowledge service returned an unexpected (non-JSON) response"}

    sources = []
    for source in data.get("sources", []):
        title = source.get("title")
        if title and title not in sources:
            sources.append(title)

    return {"answer": data.get("textResponse", ""), "sources": sources}