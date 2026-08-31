"""whiteout command line."""
from __future__ import annotations

import argparse
from typing import ClassVar, cast


class cli:
    """Namespace-only owner for the command line (snake_case by
    doctrine: it groups behavior, it is never instantiated)."""

    DEFAULT_HOST: ClassVar[str] = "127.0.0.1"
    DEFAULT_PORT: ClassVar[int] = 8000
    APP_FACTORY: ClassVar[str] = "whiteout.server.app:WhiteoutApp.create"

    @classmethod
    def run(cls) -> None:
        parser = argparse.ArgumentParser(prog="whiteout")
        commands = parser.add_subparsers(dest="command", required=True)
        serve = commands.add_parser("serve", help="run the HTTP server")
        _ = serve.add_argument("--host", default=cls.DEFAULT_HOST)
        _ = serve.add_argument("--port", type=int, default=cls.DEFAULT_PORT)
        _ = serve.add_argument("--reload", action="store_true")
        args = parser.parse_args()
        # argparse.Namespace attributes are Any; the parser setup above
        # is the contract these casts state
        if cast(str, args.command) == "serve":
            cls._serve(
                host=cast(str, args.host),
                port=cast(int, args.port),
                live_reload=cast(bool, args.reload),
            )

    @classmethod
    def _serve(cls, host: str, port: int, live_reload: bool) -> None:
        import uvicorn

        uvicorn.run(
            cls.APP_FACTORY,
            factory=True,
            host=host,
            port=port,
            reload=live_reload,
        )


def main() -> None:
    """console_scripts entry point — the composition root."""
    cli.run()
