import json

import instructor
from langchain_core.tools import BaseTool
from openai import AsyncOpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from graph.graph_utils import stringify_result
from models.plan import Plan, PlanStepArgs


async def execute_plan(plan: Plan, tools: list[BaseTool], customer_id: str, conversation_history: str) -> list[dict]:
    tools_by_name = {t.name: t for t in tools}
    observations = []

    client = instructor.from_openai(
        AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
        mode=instructor.Mode.JSON_SCHEMA,
    )

    for step in plan.steps:
        if step.tool_hint is None or step.tool_hint not in tools_by_name:
            continue  # reasoning-only step, nothing to execute

        tool = tools_by_name[step.tool_hint]

        prior = "\n".join(
            f"Step {o['step_id']} ({o['tool']}): {o['result']}"
            for o in observations
        ) or "None yet."

        schema = tool.args_schema
        if schema is None:
            schema_str = "{}"
        elif isinstance(schema, dict):
            schema_str = json.dumps(schema)
        else:
            schema_str = json.dumps(schema.model_json_schema())

        arg_prompt = f"""
You are about to call the tool "{tool.name}": {tool.description}
Tool schema: {schema_str}

Current step: {step.description}
Prior step results:
{prior}
Customer ID: {customer_id}
Conversation: {conversation_history}


Extract the arguments this tool call needs, based on the conversation
and prior results. If a required value isn't available anywhere, leave
it out rather than guessing.
"""
        try:
            step_args = await client.chat.completions.create(
                model=LLM_MODEL,
                response_model=PlanStepArgs,
                messages=[{"role": "user", "content": arg_prompt}],
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 20,
                    "min_p": 0.0,
                    "presence_penalty": 1.5,
                    "repetition_penalty": 1.0,
                }
            )
            result = await tool.ainvoke(step_args.args)
        except Exception as e:
            result = {"error": str(e)}

        observations.append({
            "step_id": str(step.step_id),
            "description": step.description,
            "tool": step.tool_hint,
            "result": stringify_result(result),
        })

    return observations
