"""
Rubato — Phase 1 skeleton.

Scope for this phase, deliberately: one endpoint, one hardcoded response.
No triage, no RAG, no graph. The point of Phase 1 is proving the scaffolding
(FastAPI app, Docker, config wiring to LM Studio) works before any real logic
goes on top of it.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import LLM_BASE_URL, LLM_MODEL
from graph.state_graph import app_graph
from models.conversation_state import ConversationState

app = FastAPI(
    title="Rubato",
    description="AI customer support copilot — portfolio project skeleton",
    version="0.1.0",
)


class SupportMessageRequest(BaseModel):
    conversation_id: str = Field(..., description="Stable ID for this conversation thread")
    customer_id: str = Field(..., description="Customer placing the request")
    message: str = Field(..., description="Raw customer message text")


class SupportMessageResponse(BaseModel):
    conversation_id: str
    reply: str
    intent: str | None = None  # populated starting Phase 2 (triage)
    trace_id: str
    responded_at: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
    }


@app.post("/support/message", response_model=SupportMessageResponse)
def support_message(payload: SupportMessageRequest) -> SupportMessageResponse:
    state = ConversationState(
        id=payload.conversation_id,
        message=payload.message,
    )

    result = app_graph.invoke(state)

    return SupportMessageResponse(
        conversation_id=payload.conversation_id,
        reply=f"{result}",
        intent=None,
        trace_id=str(uuid4()),
        responded_at=datetime.now(timezone.utc).isoformat(),
    )
