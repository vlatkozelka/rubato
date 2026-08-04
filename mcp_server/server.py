from mcp_server.instance import mcp
from mcp_server.auth import SharedKeyAuthMiddleware
import mcp_server.tools  # noqa: F401 — triggers tool registration

app = mcp.streamable_http_app()
app.add_middleware(SharedKeyAuthMiddleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_server.server:app", host="127.0.0.1", port=8001, reload=True)
