"""TimeUUID — an ObjectUUID that only accepts TIME instances."""
from __future__ import annotations

from typing import ClassVar

from nylium.Constants import Constants
from nylium.uuid.objects.TypedObjectUUID import TypedObjectUUID


class TimeUUID(TypedObjectUUID):
    TYPE_NAME: ClassVar[str] = Constants.Scalar.TIME
