from langchain_core.messages import AIMessage, ToolMessage

from models.agent_observation import AgentObservation


def build_tool_registry(tools: list) -> dict[str, str]:
    return {tool.name: tool.description for tool in tools}


def stringify_result(content) -> str:
    if isinstance(content, list):
        return " ".join(
            block.get("text", str(block)) if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def extract_observations(messages: list, tool_registry: dict[str, str]) -> list[AgentObservation]:
    call_names = {
        call["id"]: call["name"]
        for msg in messages
        if isinstance(msg, AIMessage)
        for call in (msg.tool_calls or [])
    }

    tool_messages = (msg for msg in messages if isinstance(msg, ToolMessage))

    return [
        AgentObservation(
            step_id=str(i),
            tool=(tool := call_names.get(msg.tool_call_id, "unknown")),
            description=tool_registry.get(tool,"no description available"),
            result=stringify_result(msg.content),
        )
        for i, msg in enumerate(tool_messages)
    ]
