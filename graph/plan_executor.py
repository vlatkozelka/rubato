import json

from langchain_core.tools import BaseTool

from graph.graph_utils import stringify_result
from models.llm_profile import default_non_thinking_model
from models.plan import Plan, PlanStepArgs
from services.llm_factory import get_async_instructor_client
from langfuse import get_client as get_langfuse_client


async def execute_plan(plan: Plan, tools: list[BaseTool], customer_id: str, conversation_history: str) -> list[dict]:
    tools_by_name = {t.name: t for t in tools}
    observations = []
    langfuse_client = get_langfuse_client()

    client=get_async_instructor_client(default_non_thinking_model)

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


        langfuse_arg_prompt = langfuse_client.get_prompt("agent/plan/call_tool")
        arg_prompt = langfuse_arg_prompt.compile(
            tool_name=tool.name,
            tool_description=tool.description,
            schema_str=schema_str,
            step_description=step.description,
            prior=prior,
            customer_id=customer_id,
            conversation_history=conversation_history
        )

        try:
            step_args = await client(
                prompt=langfuse_arg_prompt,
                response_model=PlanStepArgs,
                messages=[{"role": "user", "content": arg_prompt}],
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
