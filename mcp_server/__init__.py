from dotenv import load_dotenv

load_dotenv()


# Importing each tool module registers its @mcp.tool()-decorated
# functions against the shared `mcp` instance as a side effect.
# Add new tool modules here as they're created.
from mcp_server.tools import stock  # noqa: F401
from mcp_server.tools import products # noqa: F401