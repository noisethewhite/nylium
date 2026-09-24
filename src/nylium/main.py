"""nylium process entry point — the composition root."""
from __future__ import annotations

import argparse
from typing import cast

from nylium.server.serve import serve
from nylium.Constants import Constants


def main() -> None:
    """console_scripts entry point."""
    parser = argparse.ArgumentParser(prog="nylium")
    commands = parser.add_subparsers(dest="command", required=True)

    serve_parser = commands.add_parser("serve", help="run the HTTP server")
    _ = serve_parser.add_argument("--host", default=Constants.Server.DEFAULT_HOST)
    _ = serve_parser.add_argument("--port", type=int, default=Constants.Server.DEFAULT_PORT)
    _ = serve_parser.add_argument(
        "--reload", action="store_true", help="auto-reload on source changes"
    )

    args = parser.parse_args()
    if cast(str, args.command) == "serve":
        serve(
            host=cast(str, args.host),
            port=cast(int, args.port),
            live_reload=cast(bool, args.reload),
        )


if __name__ == "__main__":
    main()
