from langchain_core.tools import tool

from app.services.web_search import search_web
from app.services.web_scraper import scrape_url


@tool
def search_web_tool(query: str) -> list[dict]:
    """Search the web for a topic. Returns a list of results, each with
    title, url and a short snippet. Use this first to find candidate pages,
    then use scrape_url_tool on the most relevant url(s) to get full content."""
    return search_web(query)


@tool
def scrape_url_tool(url: str) -> dict:
    """Fetch a web page and extract its main text content and image urls.
    Use this on a url returned by search_web_tool to get the full article
    text and images before writing the blog post."""
    return scrape_url(url)


BLOG_TOOLS = [search_web_tool, scrape_url_tool]
BLOG_TOOLS_BY_NAME = {tool_.name: tool_ for tool_ in BLOG_TOOLS}
