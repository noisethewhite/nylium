"""Typed object references: ``ObjectUUID`` subclasses that verify the
instance's type on construction."""
from nylium.uuid.objects.ArrayUUID import ArrayUUID
from nylium.uuid.objects.BooleanUUID import BooleanUUID
from nylium.uuid.objects.ColorUUID import ColorUUID
from nylium.uuid.objects.DateUUID import DateUUID
from nylium.uuid.objects.DatetimeUUID import DatetimeUUID
from nylium.uuid.objects.IntegerUUID import IntegerUUID
from nylium.uuid.objects.MonthDayTimeUUID import MonthDayTimeUUID
from nylium.uuid.objects.MonthDayUUID import MonthDayUUID
from nylium.uuid.objects.NumericUUID import NumericUUID
from nylium.uuid.objects.StringUUID import StringUUID
from nylium.uuid.objects.TimeUUID import TimeUUID


__all__ = ['ArrayUUID', 'BooleanUUID', 'ColorUUID', 'DateUUID', 'DatetimeUUID', 'IntegerUUID', 'MonthDayTimeUUID', 'MonthDayUUID', 'NumericUUID', 'StringUUID', 'TimeUUID']
