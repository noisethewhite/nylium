from __future__ import annotations
from nylium.basic import EnvEnum

class Environment(EnvEnum):
    database_url = "DATABASE_URL"
    rp_id = "RP_ID"
    rp_origin = "RP_ORIGIN"
    # ADR-0006: blob storage directory (prod sets it to /opt/nylium/files)
    files_dir = "FILES_DIR"
