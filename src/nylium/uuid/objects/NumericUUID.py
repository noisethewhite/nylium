"""NumericUUID — an ObjectUUID that only accepts NUMERIC instances."""
from __future__ import annotations

from typing import ClassVar

from nylium.Constants import Constants
from nylium.uuid.objects.TypedObjectUUID import TypedObjectUUID


class NumericUUID(TypedObjectUUID):
    TYPE_NAME: ClassVar[str] = Constants.Scalar.NUMERIC
