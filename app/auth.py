import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import decode_access_token
from models.auth_principal import AuthPrincipal
from models.user_role import UserRole

logger = logging.getLogger("rubato.auth")

_bearer_scheme = HTTPBearer()


def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthPrincipal:
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def require_staff(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    if principal.role != UserRole.STAFF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return principal


def require_customer(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    if principal.role != UserRole.CUSTOMER or principal.customer_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")
    return principal
