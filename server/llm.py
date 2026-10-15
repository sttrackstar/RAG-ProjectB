import json
import os

import requests


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

    payload = {"model": model, "messages": messages, "stream": False}
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
