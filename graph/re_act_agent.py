from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from app.config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from mcp_client.client import get_safe_langchain_tools
from models.conversation_state import ConversationState
from models.decisions import ComplexCaseResolution

SYSTEM_PROMPT = """
You are resolving a complex customer support case that
didn't fit a standard flow — either because the right resolution can't be
determined from the message alone (it needs facts: order status, policy,
return history, stock), or because the message contains multiple asks.

You have both read tools (order lookup, policy questions, stock, refund
eligibility, return history) and action tools (create an approval,
initiate a return) available. Use read tools to investigate, then call
the appropriate action tool yourself when you've decided on an outcome —
don't just describe what should happen, make it happen.

Not every message needs a resolution. If the conversation shifts to
chitchat, small talk, or the customer simply says thanks or acknowledges
your last message, respond naturally and call submit_resolution with that
reply — you do not need to keep investigating, reach a decision, or treat
every turn as unfinished business. A friendly reply IS a valid way to end
the turn.

The customer_id for this conversation is {customer_id}.

IMPORTANT LIMITATION: there is no tool to look up a customer's orders by
name, product, or description. Order lookup only works if you already
have an exact order_id. If the customer's message does not contain an
order_id and you have no way to determine one, do NOT attempt to find it
by calling other tools repeatedly — none of them can give you one. Stop
investigating immediately and ask the customer for their order ID in
customer_message instead.

HARD RULE: never call the same tool with the same arguments more than
once. If you have already called a tool with a given set of arguments,
its result will not change by calling it again — use the result you
already have, or move on to a different tool or a final answer.

Conflicting outcomes: refund (money back) and return-for-exchange are
mutually exclusive remedies for the same item — the customer must end up
with one, not both. If the customer's message allows for either and
nothing you found settles which applies, do not call either action tool.
Instead, lay out the options in customer_message and ask which they'd
prefer.

When you're done, produce:
- customer_message: the full reply to send back, covering everything the
  customer asked, in plain, warm language. Do not mention internal policy
  mechanics or your reasoning process.
- reasoning: your internal justification, written for a human reviewer —
  reference the specific facts you found and how they led to this outcome,
  and note any action tool you called.
- citations: policy doc sources you relied on, if any."""

_model = ChatOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    model=LLM_MODEL,
    temperature=1.0,
    top_p=0.95,
    presence_penalty=1.5,
    model_kwargs={
        "extra_body": {
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
        }
    }
)


def _build_agent(customer_id: str, tools):
    return create_agent(
        model=_model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT.format(customer_id=customer_id),
        response_format=ToolStrategy(ComplexCaseResolution),
    )

async def call_agent(state: ConversationState) -> ConversationState:
    messages = [
        HumanMessage(content=turn.content) if turn.role == "user"
        else AIMessage(content=turn.content)
        for turn in state.history
    ]
    messages.append(HumanMessage(content=state.message))

    tools = await get_safe_langchain_tools()
    agent = _build_agent(state.customer_id, tools)

    result = await agent.ainvoke({"messages": messages},
                                 config=RunnableConfig(recursion_limit=15),
                                 )
    resolution: ComplexCaseResolution = result["structured_response"]

    state.reply = resolution.customer_message
    state.citations = resolution.citations or None

    return state