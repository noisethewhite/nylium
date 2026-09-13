from __future__ import annotations
from pathlib import Path
from typing import override

from nylium.basic import EnvEnum

class Environment(EnvEnum):
    database_url = "DATABASE_URL"
    rp_id = "RP_ID"
    rp_origin = "RP_ORIGIN"
    # ADR-0006: blob storage directory (prod sets it to /opt/nylium/files)
    files_dir = "FILES_DIR"
    # Optional: built frontend bundle location, defaults to the in-repo build
    web_dist = "NYLIUM_WEB_DIST"

    @override
    def _default(self) -> str:
        # Compare by name: touching Environment.web_dist here would recurse
        # through EnvEnum.__get__ straight back into this method.
        if self.name == "web_dist":
            return str(Path("web") / "dist")
        return ""
