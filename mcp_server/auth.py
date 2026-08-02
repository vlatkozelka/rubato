from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os
import secrets

class SharedKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "missing bearer token"}, status_code=401)

        token = auth_header.removeprefix("Bearer ")
        expected = os.environ["MCP_SHARED_KEY"]
        if not secrets.compare_digest(token, expected):
            return JSONResponse({"error": "invalid token"}, status_code=401)

        return await call_next(request)