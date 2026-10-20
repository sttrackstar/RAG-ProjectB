from tools.search_knowledge import search_knowledge
from tools.web_search import web_search
from tools.save_note import save_note

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
    "web_search": {
        "function": web_search,
        "schema": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the open web (Wikipedia) for general or public information "
                    "that is NOT in the team's internal knowledge base, such as background "
                    "on technologies, people, or concepts. Returns article titles, URLs, "
                    "and short summaries. Try search_knowledge first for questions about "
                    "Acme or Nimbus Notes."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search terms, e.g. 'vector database'"}
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "save_note": {
        "function": save_note,
        "requires_confirmation": True,
        "schema": {
            "type": "function",
            "function": {
                "name": "save_note",
                "description": (
                    "Save a research note for the user. Only use this when the user "
                    "explicitly asks to save or remember something. The user will be "
                    "asked to confirm before the note is saved."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short title for the note"},
                        "content": {"type": "string", "description": "The note text, including sources"},
                    },
                    "required": ["title", "content"],
                },
            },
        },
    },
}


def tool_schemas() -> list:
    return [tool["schema"] for tool in TOOLS.values()]
