import logging
from typing import List, Optional
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.config import POSTGRES_DSN
from models.approval import Approval, ApprovalPayload, ApprovalStatus
from services.order_service import get_order_by_id
from services.refund_execution_service import execute_refund

logger = logging.getLogger("rubato.services.approval")

_COLUMNS = "id, type, status, payload, reason, created_at, updated_at"


def _row_to_approval(row) -> Approval:
    id_, type_, status_, payload, reason, created_at, updated_at = row
    return Approval(
        id=id_,
        type=type_,
        status=status_,
        payload=ApprovalPayload(**payload),
        reason=reason,
        created_at=created_at.isoformat(),
        updated_at=updated_at.isoformat(),
    )


async def create_approval(approval: Approval) -> Approval:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"""
        INSERT INTO approvals (id, type, status, payload, reason, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING {_COLUMNS}
        """,
        (
            str(approval.id),
            approval.type.value,
            approval.status.value,
            Jsonb(approval.payload.model_dump()),
            approval.reason,
            approval.created_at,
            approval.updated_at,
        ),
    )
    row = await cur.fetchone()
    await conn.commit()
    await cur.close()
    await conn.close()
    return _row_to_approval(row)


async def list_pending() -> List[Approval]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"SELECT {_COLUMNS} FROM approvals WHERE status = %s ORDER BY created_at",
        (ApprovalStatus.PENDING_REVIEW.value,),
    )
    rows = await cur.fetchall()
    await cur.close()
    await conn.close()
    return [_row_to_approval(r) for r in rows]


async def deny(approval_id: UUID, reason: str) -> Optional[Approval]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"""
        UPDATE approvals
        SET status = %s, reason = %s, updated_at = now()
        WHERE id = %s AND status = %s
        RETURNING {_COLUMNS}
        """,
        (ApprovalStatus.DENIED.value, reason, str(approval_id), ApprovalStatus.PENDING_REVIEW.value),
    )
    row = await cur.fetchone()
    await conn.commit()
    await cur.close()
    await conn.close()
    return _row_to_approval(row) if row else None


async def approve(approval_id: UUID) -> Optional[Approval]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"SELECT {_COLUMNS} FROM approvals WHERE id = %s AND status = %s",
        (str(approval_id), ApprovalStatus.PENDING_REVIEW.value),
    )
    row = await cur.fetchone()
    await cur.close()
    await conn.close()
    if row is None:
        return None

    approval = _row_to_approval(row)

    order = await get_order_by_id(approval.payload.order_id)
    if order is None:
        logger.warning(
            "approve_order_not_found",
            extra={"event": "approve_order_not_found", "order_id": approval.payload.order_id},
        )
        return None

    # Amount the customer actually paid, from the order snapshot taken at
    # purchase time — never the product's current (possibly drifted) price.
    amount = order.total
    approval.payload.amount = amount

    execute_refund(order.id, amount)

    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"""
        UPDATE approvals
        SET status = %s, payload = %s, updated_at = now()
        WHERE id = %s
        RETURNING {_COLUMNS}
        """,
        (ApprovalStatus.APPROVED.value, Jsonb(approval.payload.model_dump()), str(approval_id)),
    )
    updated_row = await cur.fetchone()
    await conn.commit()
    await cur.close()
    await conn.close()
    return _row_to_approval(updated_row)
