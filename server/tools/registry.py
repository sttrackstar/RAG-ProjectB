from tools.search_knowledge import search_knowledge

# Every tool the agent can use. "schema" is what the model sees;
# "function" is what our code runs when the model asks for it.
TOOLS = {
    "search_knowledge": {
        "function": search_knowledge,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": (
                    "Search the team's internal knowledge base (company policies, "
                    "product FAQs, technical notes). Use this for any question about "
                    "Acme, Nimbus Notes, or vector search before answering."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to look up"}
                    },
                    "required": ["query"],
                },
            },
        },
    },
}


def tool_schemas() -> list:
    return [tool["schema"] for tool in TOOLS.values()]
