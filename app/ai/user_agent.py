from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from app.ai.llm import LLMService
from app.ai.user_tools import activate_user_tool, deactivate_user_tool

MAX_STEPS = 5

ACTION_TOOLS = [activate_user_tool, deactivate_user_tool]
ACTION_TOOLS_BY_NAME = {t.name: t for t in ACTION_TOOLS}
ACTION_BY_TOOL_NAME = {
    "activate_user_tool": "activate",
    "deactivate_user_tool": "deactivate",
}

FIND_USER_SYSTEM_PROMPT = (
    "You have two tools:\n"
    "- activate_user_tool(name): use when the admin wants to activate/enable a user\n"
    "- deactivate_user_tool(name): use when the admin wants to deactivate/disable/inactivate a user\n"
    "Extract the person's name or email from the admin's request and call the "
    "matching tool with it."
)


def find_users_from_query(query: str) -> dict:
    """Returns {"action": "activate"|"deactivate"|None, "matches": [...]}"""
    tool_model = LLMService.get_tool_model().bind_tools(ACTION_TOOLS)

    messages = [
        SystemMessage(content=FIND_USER_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]

    for _ in range(MAX_STEPS):
        response = tool_model.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            messages.append(HumanMessage(content=(
                "Now call activate_user_tool or deactivate_user_tool with the "
                "person's name or email from the request above."
            )))
            continue

        for call in tool_calls:
            tool_fn = ACTION_TOOLS_BY_NAME.get(call["name"])
            if tool_fn is None:
                messages.append(ToolMessage(
                    content="unknown tool",
                    tool_call_id=call["id"],
                ))
                continue

            try:
                result = tool_fn.invoke(call["args"])
            except Exception:
                result = []

            return {
                "action": ACTION_BY_TOOL_NAME.get(call["name"]),
                "matches": result if isinstance(result, list) else [],
            }

    return {"action": None, "matches": []}
