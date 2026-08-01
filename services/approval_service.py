import logging
from typing import Optional
from uuid import UUID

import psycopg

from app.config import POSTGRES_DSN
from models.approval import Approval, ApprovalPayload

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


def list_pending_approvals() -> list[Approval]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(f"SELECT {_COLUMNS} FROM approvals WHERE status = 'pending_review' ORDER BY created_at")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_approval(r) for r in rows]


def set_approval_status(approval_id: UUID, new_status: str) -> Optional[Approval]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE approvals SET status = %s WHERE id = %s RETURNING {_COLUMNS}",
        (new_status, str(approval_id)),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return _row_to_approval(row) if row else None
