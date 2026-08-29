from typing import Any


async def search_web(query: str) -> list[dict[str, Any]]:
    """Search interface reserved for a future web search integration."""

    # TODO: Connect this interface to a web search provider.
    return [{"query": query, "source": "mock", "content": ""}]
