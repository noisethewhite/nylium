"""IntegerUUID — an ObjectUUID that only accepts INTEGER instances."""
from __future__ import annotations

from typing import ClassVar

from nylium.Constants import Constants
from nylium.uuid.objects.TypedObjectUUID import TypedObjectUUID


class IntegerUUID(TypedObjectUUID):
    TYPE_NAME: ClassVar[str] = Constants.Scalar.INTEGER
