"""MonthDayUUID — an ObjectUUID that only accepts MONTH_DAY instances."""
from __future__ import annotations

from typing import ClassVar

from nylium.Constants import Constants
from nylium.uuid.objects.TypedObjectUUID import TypedObjectUUID


class MonthDayUUID(TypedObjectUUID):
    TYPE_NAME: ClassVar[str] = Constants.Scalar.MONTH_DAY
