import json

def unwrap_tool_result(result: list[dict]) -> list[dict]:
    return [json.loads(block["text"]) for block in result]