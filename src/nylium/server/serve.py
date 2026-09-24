"""HTTP server launch — uvicorn around the NyliumApp factory."""
from __future__ import annotations

import uvicorn
from nylium.Constants import Constants



def serve(host: str = Constants.Server.DEFAULT_HOST, port: int = Constants.Server.DEFAULT_PORT, *, live_reload: bool = False) -> None:
    """Run the HTTP server in the foreground."""
    uvicorn.run(
        Constants.Server.APP_FACTORY,
        factory=True,
        host=host,
        port=port,
        reload=live_reload,
    )
