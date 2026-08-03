from dotenv import load_dotenv

load_dotenv()


# Importing each tool module registers its @mcp.tool()-decorated
# functions against the shared `mcp` instance as a side effect.
# Add new tool modules here as they're created.
from mcp_server.tools import stock  # noqa: F401
from mcp_server.tools import products # noqa: F401
from mcp_server.tools import orders  # noqa: F401
from mcp_server.tools import triage  # noqa: F401
from mcp_server.tools import policy  # noqa: F401
from mcp_server.tools import refunds  # noqa: F401
from mcp_server.tools import returns  # noqa: F401
from mcp_server.tools import approvals  # noqa: F401
from mcp_server.tools import return_history  # noqa: F401