from __future__ import annotations
from typing import ClassVar
from nylium.data.types.MonthDay import MonthDay
from typing import Self
from dataclasses import dataclass
from datetime import date
from typing import override
import re
from datetime import time


@dataclass(frozen=True, slots=True)
class MonthDayTime:
    """A MonthDay with a wall-clock time — yearly recurring alarms."""

    month: int
    day: int
    hour: int
    minute: int

    PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(\d{2})-(\d{2})T(\d{2}):(\d{2})$")

    def __post_init__(self) -> None:
        _ = date(MonthDay.LEAP_YEAR, self.month, self.day)
        _ = time(self.hour, self.minute)

    @classmethod
    def parse(cls, raw: str) -> Self:
        match = cls.PATTERN.match(raw)
        if match is None:
            raise ValueError(f"not an MM-DDTHH:MM stamp: {raw!r}")
        return cls(*(int(group) for group in match.groups()))

    @override
    def __str__(self) -> str:
        return f"{self.month:02d}-{self.day:02d}T{self.hour:02d}:{self.minute:02d}"
