from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from models.auth_principal import AuthPrincipal
from models.user_role import UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject_id: str, role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject_id,
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> AuthPrincipal:
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    role = UserRole(payload["role"])
    sub = payload["sub"]
    return AuthPrincipal(
        sub=sub,
        role=role,
        # A customer's own id IS their login row's id, so sub already *is*
        # the customer_id for that role — no separate claim to carry.
        customer_id=sub if role == UserRole.CUSTOMER else None,
    )
