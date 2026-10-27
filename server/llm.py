import json
import os

import requests


def warm_up() -> dict:
    """Load the agent model into memory without asking it anything.

    Called when a user starts typing, so the model is ready by the time they
    ask (a cold start can take 20-50 seconds; a loaded model about 6).
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("AGENT_MODEL", "llama3.1:8b")
    keep_alive = os.environ.get("OLLAMA_KEEP_ALIVE", "1h")
    timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))

    try:
        response = requests.post(
            f"{base_url}/api/generate", json={"model": model, "keep_alive": keep_alive}, timeout=timeout
        )
        response.raise_for_status()
    except requests.RequestException:
        return {"warm": False, "error": "Could not load the model - is Ollama running?"}
    return {"warm": True}


def generate(messages: list, tools: list | None = None) -> dict:
    """Ask the agent model what to do next.

    Returns one of:
      {"type": "tool_calls", "tool_calls": [{"name": str, "arguments": dict}], "message": dict}
      {"type": "final", "content": str, "message": dict}
      {"type": "error", "error": str}
    "message" is the model's raw reply, so the agent loop can add it to the history.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("AGENT_MODEL", "llama3.1:8b")
    timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
    keep_alive = os.environ.get("OLLAMA_KEEP_ALIVE", "1h")

    # keep_alive stops Ollama unloading the model after its default 5 idle minutes.
    payload = {"model": model, "messages": messages, "stream": False, "keep_alive": keep_alive}
    if tools:
        payload["tools"] = tools

    try:
        response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout:
        return {"type": "error", "error": f"Model timed out after {timeout:g}s"}
    except requests.ConnectionError:
        return {"type": "error", "error": "Model service is unreachable - is Ollama running?"}
    except requests.HTTPError:
        return {"type": "error", "error": f"Model service returned HTTP {response.status_code}"}

    try:
        message = response.json()["message"]
    except (ValueError, KeyError, TypeError):
        return {"type": "error", "error": "Model service returned an unexpected response"}

    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function", {})
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                pass  # leave the raw string; argument validation will reject it
        tool_calls.append({"name": function.get("name"), "arguments": arguments})

    if tool_calls:
        return {"type": "tool_calls", "tool_calls": tool_calls, "message": message}
    return {"type": "final", "content": message.get("content", ""), "message": message}
