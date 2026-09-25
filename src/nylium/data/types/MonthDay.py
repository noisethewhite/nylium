from __future__ import annotations
from typing import ClassVar
from typing import Self
from dataclasses import dataclass
from datetime import date
from typing import override
import re


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
