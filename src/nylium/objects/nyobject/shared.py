from __future__ import annotations
from pydantic import ConfigDict


CONFIG = ConfigDict(extra="ignore")


# The object title prop, pinned first on every object type (see
# api.shared.NAME_PROP_KEY). Tags derive the owner's display name from it.
NAME_PROP_KEY = "name"
