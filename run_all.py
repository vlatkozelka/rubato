import asyncio
import sys

import uvicorn


async def main():
    config1 = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
    config2 = uvicorn.Config(
        "mcp_server.server:app",
        host="127.0.0.1",
        port=8001,
        reload=True
    )
    server1 = uvicorn.Server(config1)
    server2 = uvicorn.Server(config2)
    await asyncio.gather(server1.serve(), server2.serve())


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
