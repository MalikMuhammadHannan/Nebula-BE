from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from app.ai.llm import LLMService
from app.ai.user_tools import find_user_tool

MAX_STEPS = 5

FIND_USER_SYSTEM_PROMPT = (
    "You have one tool: find_user_tool(name). Extract the person's name or email from "
    "the admin's request and call find_user_tool with it."
)


def find_users_from_query(query: str) -> list[dict]:
    tool_model = LLMService.get_tool_model().bind_tools([find_user_tool])

    messages = [
        SystemMessage(content=FIND_USER_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]

    for _ in range(MAX_STEPS):
        response = tool_model.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            messages.append(HumanMessage(
                content="Now call find_user_tool with the person's name from the request above."
            ))
            continue

        for call in tool_calls:
            if call["name"] != "find_user_tool":
                messages.append(ToolMessage(
                    content="unknown tool",
                    tool_call_id=call["id"],
                ))
                continue

            try:
                result = find_user_tool.invoke(call["args"])
            except Exception:
                result = []

            return result if isinstance(result, list) else []

    return []
