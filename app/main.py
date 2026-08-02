"""
Rubato — Phase 1 skeleton.

Scope for this phase, deliberately: one endpoint, one hardcoded response.
No triage, no RAG, no graph. The point of Phase 1 is proving the scaffolding
(FastAPI app, Docker, config wiring to LM Studio) works before any real logic
goes on top of it.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import require_customer
from app.config import BASE_DIR, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, LLM_BASE_URL, LLM_MODEL
from app.conversation_log_filter import conversation_context
from app.logging_setup import configure_logging
from app.security import create_access_token
from app.timing import log_duration
from graph.state_graph import app_graph
from models.auth_principal import AuthPrincipal
from models.conversation_state import ConversationState
from models.intent import Intent
from models.user_role import UserRole
from routers.approvals import router as approvals_router
from routers.products import router as products_router
from services.customer_auth_service import authenticate_customer
from services.staff_auth_service import authenticate_staff

STATIC_DIR = BASE_DIR / "static"

configure_logging()
logger = logging.getLogger("rubato.api")

_MESSAGE_PREVIEW_CHARS = 200

app = FastAPI(
    title="Rubato",
    description="AI customer support copilot — portfolio project skeleton",
    version="0.1.0",
)
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
app.include_router(approvals_router)
app.include_router(products_router)


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
    intent: Optional[Intent] = None
    citations: Optional[List[str]] = None
    trace_id: str
    responded_at: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
    }


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/login")


@app.get("/login")
def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/chat")
def chat_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "chat.html")


@app.get("/admin")
def admin_login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin_login.html")


@app.get("/admin/dashboard")
def admin_dashboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin_dashboard.html")


def _issue_token(subject_id: str, role: UserRole) -> LoginResponse:
    token = create_access_token(subject_id, role)
    return LoginResponse(access_token=token, expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@app.post("/auth/customer/login", response_model=LoginResponse)
def customer_login(payload: LoginRequest) -> LoginResponse:
    customer = authenticate_customer(payload.email, payload.password)
    if customer is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _issue_token(customer.id, UserRole.CUSTOMER)


@app.post("/auth/staff/login", response_model=LoginResponse)
def staff_login(payload: LoginRequest) -> LoginResponse:
    staff = authenticate_staff(payload.email, payload.password)
    if staff is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _issue_token(staff.id, UserRole.STAFF)


def _build_support_response(conversation_id: str, result_state: ConversationState) -> SupportMessageResponse:
    # Maps internal ConversationState.results onto the API's chat shape — see DECISIONS.md.
    non_empty = [r for r in result_state.results if r.result]
    if not non_empty:
        reply = "Sorry, I wasn't able to process that."
        intent = None
        citations = None
    else:
        reply = "\n\n".join(r.result for r in non_empty)
        final = non_empty[-1]
        intent = final.intent
        citations = final.citations

    return SupportMessageResponse(
        conversation_id=conversation_id,
        reply=reply,
        intent=intent,
        citations=citations,
        trace_id=str(uuid4()),
        responded_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/support/message", response_model=SupportMessageResponse)
async def support_message(
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
                customer_id=customer_id,
            )

            raw_result = await app_graph.ainvoke(state)
            result_state = ConversationState.model_validate(raw_result)

            response = _build_support_response(payload.conversation_id, result_state)

        return response
