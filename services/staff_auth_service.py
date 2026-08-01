import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from app.security import verify_password
from models.staff_user import StaffUser

logger = logging.getLogger("rubato.services.staff_auth")


def authenticate_staff(email: str, password: str) -> Optional[StaffUser]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password_hash, created_at FROM staff_users WHERE email = %s",
        (email,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    staff_id, staff_email, password_hash, created_at = row
    if not verify_password(password, password_hash):
        return None

    return StaffUser(id=str(staff_id), email=staff_email, created_at=created_at.isoformat())
