from tavily import TavilyClient

from app.config import TAVILY_API_KEY

_client = TavilyClient(api_key=TAVILY_API_KEY)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    response = _client.search(
        query=query,
        max_results=max_results,
        include_images=True,
    )

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("content", ""),
        }
        for result in response.get("results", [])
    ]
