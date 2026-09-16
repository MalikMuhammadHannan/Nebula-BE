import re

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from app.ai.llm import LLMService
from app.ai.blog_tools import BLOG_TOOLS, BLOG_TOOLS_BY_NAME
from app.services.web_scraper import scrape_url

_TAG_RE = re.compile(r"<[^>]+>")
_LABEL_RE = re.compile(r"\b(TITLE|DESCRIPTION|CONTENT)\s*:\s*", re.IGNORECASE)

MAX_TOOL_STEPS = 8

RESEARCH_SYSTEM_PROMPT = """You are a research assistant with two tools:
- search_web_tool(query): search the web for pages about a topic
- scrape_url_tool(url): fetch a page's full text and images

Use these tools to research the user's topic before answering."""

WRITE_PROMPT_TEMPLATE = """Using only the information gathered above, write a blog post about: {query}

Respond in exactly this format:
TITLE: <a short, engaging title>
DESCRIPTION: <one short sentence summary>
CONTENT: <2-4 paragraphs for the blog post, based only on the information above>"""


def _parse_blog_text(text: str) -> dict:
    # Models occasionally wrap the answer in stray HTML tags despite being
    # asked for plain text -- strip them so label matching isn't thrown off.
    clean = _TAG_RE.sub(" ", text)
    clean = re.sub(r"[ \t]+", " ", clean).strip()

    labels = list(_LABEL_RE.finditer(clean))
    fields = {"title": "", "description": "", "content": ""}

    for i, match in enumerate(labels):
        key = match.group(1).lower()
        start = match.end()
        end = labels[i + 1].start() if i + 1 < len(labels) else len(clean)
        value = clean[start:end].strip()
        if not fields[key]:
            fields[key] = value

    title, description, content = fields["title"], fields["description"], fields["content"]

    if not content:
        # The model often skips the CONTENT label and dumps everything into
        # DESCRIPTION instead -- treat that as the real content and derive a
        # fresh short description from it below, rather than duplicating it.
        content = description or clean
        description = ""

    if not title:
        words = content.split()
        title = " ".join(words[:8]) + ("..." if len(words) > 8 else "")

    if not description:
        sentences = [s.strip() for s in content.replace("\n", " ").split(". ") if s.strip()]
        description = sentences[0] if sentences else content[:140]
        if not description.endswith("."):
            description += "."

    return {"title": title, "description": description, "content": content}


def _scrape_with_fallback(requested_url: str, candidate_urls: list[str], tried: set[str]) -> dict:
    """Try the model's requested url first; if it comes back empty (dead link,
    bot-blocked, etc.), fall back to other urls from the same search results
    ourselves rather than asking the model to pick a different one -- a 0.5B
    model reliably fixates on repeating the same url when asked to retry."""
    urls_to_try = [requested_url] + [u for u in candidate_urls if u and u not in tried and u != requested_url]

    result = {"url": requested_url, "text": "", "images": []}
    for url in urls_to_try:
        tried.add(url)
        result = scrape_url(url)
        if result.get("text"):
            break
    return result


def generate_blog_from_query(query: str) -> dict | None:
    tool_model = LLMService.get_tool_model().bind_tools(BLOG_TOOLS)

    messages = [
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Research this topic: {query}"),
    ]

    images: list[str] = []
    scraped_any = False
    tried_urls: set[str] = set()
    last_search_urls: list[str] = []

    for _ in range(MAX_TOOL_STEPS):
        response = tool_model.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            if scraped_any:
                break
            messages.append(HumanMessage(content=(
                "Now call scrape_url_tool on the single most relevant url from the "
                "search results above, to get its full text and images."
            )))
            continue

        for call in tool_calls:
            tool_fn = BLOG_TOOLS_BY_NAME.get(call["name"])
            if tool_fn is None:
                result = {"error": f"Unknown tool {call['name']}"}
            elif call["name"] == "scrape_url_tool":
                requested_url = str(call["args"].get("url", ""))
                result = _scrape_with_fallback(requested_url, last_search_urls, tried_urls)
                if result.get("text"):
                    scraped_any = True
                    images.extend(result.get("images", []))
            else:
                try:
                    result = tool_fn.invoke(call["args"])
                except Exception as e:
                    result = {"error": str(e)}

                if call["name"] == "search_web_tool" and isinstance(result, list):
                    last_search_urls = [r.get("url", "") for r in result if isinstance(r, dict)]

            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=call["id"],
            ))

        if scraped_any:
            break

    if not scraped_any:
        return None

    messages.append(HumanMessage(content=WRITE_PROMPT_TEMPLATE.format(query=query)))
    final_response = LLMService.get_model().invoke(messages)
    final_text = (final_response.content or "").strip()


    if not final_text:
        return None

    parsed = _parse_blog_text(final_text)
    parsed["images"] = images
    return parsed
