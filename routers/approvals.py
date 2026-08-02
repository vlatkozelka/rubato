from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_staff
from models.approval import Approval
from models.auth_principal import AuthPrincipal
from services.approval_service import approve, deny, list_pending

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DenyRequest(BaseModel):
    reason: str


@router.get("", response_model=List[Approval])
async def get_approvals(_: AuthPrincipal = Depends(require_staff)) -> List[Approval]:
    return await list_pending()


@router.post("/{approval_id}/approve", response_model=Approval)
async def approve_approval(approval_id: UUID, _: AuthPrincipal = Depends(require_staff)) -> Approval:
    approval = await approve(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found or not pending")
    return approval


@router.post("/{approval_id}/deny", response_model=Approval)
async def deny_approval(
    approval_id: UUID,
    payload: DenyRequest,
    _: AuthPrincipal = Depends(require_staff),
) -> Approval:
    approval = await deny(approval_id, payload.reason)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found or not pending")
    return approval
