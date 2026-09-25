"""StringUUID — an ObjectUUID that only accepts STRING instances."""
from __future__ import annotations

from typing import ClassVar

from nylium.Constants import Constants
from nylium.uuid.objects.TypedObjectUUID import TypedObjectUUID


class StringUUID(TypedObjectUUID):
    TYPE_NAME: ClassVar[str] = Constants.Scalar.STRING
