"""HTTP server launch — uvicorn around the NyliumApp factory."""
from __future__ import annotations

import uvicorn

APP_FACTORY = "nylium.server.app:NyliumApp.create"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *, live_reload: bool = False) -> None:
    """Run the HTTP server in the foreground."""
    uvicorn.run(
        APP_FACTORY,
        factory=True,
        host=host,
        port=port,
        reload=live_reload,
    )
