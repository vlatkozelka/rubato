import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from app.security import verify_password
from models.user import User
from models.user_role import UserRole

logger = logging.getLogger("rubato.services.user")


def authenticate_user(email: str, password: str) -> Optional[User]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password_hash, role, customer_id, created_at FROM users WHERE email = %s",
        (email,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    user_id, user_email, password_hash, role, customer_id, created_at = row
    if not verify_password(password, password_hash):
        return None

    return User(
        id=str(user_id),
        email=user_email,
        role=UserRole(role),
        customer_id=customer_id,
        created_at=created_at.isoformat(),
    )
