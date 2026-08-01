"""
Rubato — Phase 1 skeleton.

Scope for this phase, deliberately: one endpoint, one hardcoded response.
No triage, no RAG, no graph. The point of Phase 1 is proving the scaffolding
(FastAPI app, Docker, config wiring to LM Studio) works before any real logic
goes on top of it.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_customer, require_staff
from app.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, LLM_BASE_URL, LLM_MODEL
from app.conversation_log_filter import conversation_context
from app.logging_setup import configure_logging
from app.security import create_access_token
from app.timing import log_duration
from graph.state_graph import app_graph
from models.approval import Approval
from models.auth_principal import AuthPrincipal
from models.conversation_state import ConversationState
from services.approval_service import list_pending_approvals, set_approval_status
from services.user_service import authenticate_user

configure_logging()
logger = logging.getLogger("rubato.api")

_MESSAGE_PREVIEW_CHARS = 200

app = FastAPI(
    title="Rubato",
    description="AI customer support copilot — portfolio project skeleton",
    version="0.1.0",
)


def _preview(text: str, limit: int = _MESSAGE_PREVIEW_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


class SupportMessageRequest(BaseModel):
    conversation_id: str = Field(..., description="Stable ID for this conversation thread")
    message: str = Field(..., description="Raw customer message text")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


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


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user)
    return LoginResponse(access_token=token, expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@app.get("/approvals", response_model=list[Approval])
def get_approvals(_: AuthPrincipal = Depends(require_staff)) -> list[Approval]:
    return list_pending_approvals()


@app.post("/approvals/{approval_id}/approve", response_model=Approval)
def approve_approval(approval_id: UUID, _: AuthPrincipal = Depends(require_staff)) -> Approval:
    approval = set_approval_status(approval_id, "approved")
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/approvals/{approval_id}/deny", response_model=Approval)
def deny_approval(approval_id: UUID, _: AuthPrincipal = Depends(require_staff)) -> Approval:
    approval = set_approval_status(approval_id, "denied")
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/support/message", response_model=SupportMessageResponse)
def support_message(
    payload: SupportMessageRequest,
    principal: AuthPrincipal = Depends(require_customer),
) -> SupportMessageResponse:
    customer_id = principal.customer_id
    with conversation_context(payload.conversation_id):
        logger.info(
            "request_received",
            extra={
                "event": "request_received",
                "customer_id": customer_id,
                "message_preview": _preview(payload.message),
            },
        )

        with log_duration(logger, "request_finished"):
            state = ConversationState(
                id=payload.conversation_id,
                message=payload.message,
            )

            result = app_graph.invoke(state)

            response = SupportMessageResponse(
                conversation_id=payload.conversation_id,
                reply=f"{result}",
                intent=None,
                trace_id=str(uuid4()),
                responded_at=datetime.now(timezone.utc).isoformat(),
            )

        return response
