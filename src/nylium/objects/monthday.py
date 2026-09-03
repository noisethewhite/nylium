"""Year-less calendar values: MonthDay and MonthDayTime.

No year exists to hang a real date on, so these are small immutable
value classes stored as text stamps: "MM-DD" and "MM-DDTHH:MM".
Validation runs through the proleptic calendar pinned to a leap year,
which keeps 02-29 representable while rejecting 02-31 and friends.

File-level exception to one-class-per-file: two peer value types
expressing one idea (a calendar stamp without a year), mirroring
wscalar.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time
from typing import ClassVar, Self, override


@dataclass(frozen=True, slots=True)
class MonthDay:
    """A month/day pair without a year — birthdays, anniversaries."""

    month: int
    day: int

    PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(\d{2})-(\d{2})$")
    # a leap year, so the calendar check below accepts 02-29
    LEAP_YEAR: ClassVar[int] = 2000

    def __post_init__(self) -> None:
        _ = date(MonthDay.LEAP_YEAR, self.month, self.day)

    @classmethod
    def parse(cls, raw: str) -> Self:
        match = cls.PATTERN.match(raw)
        if match is None:
            raise ValueError(f"not an MM-DD stamp: {raw!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    @override
    def __str__(self) -> str:
        return f"{self.month:02d}-{self.day:02d}"


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
