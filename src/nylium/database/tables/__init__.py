# One file per table; this package keeps the old flat import surface:
# `from nylium.database.tables import Types` works exactly as before.
from nylium.database.tables.base import Base
from nylium.database.tables.types import Types
from nylium.database.tables.props import Props
from nylium.database.tables.instances import Instances
from nylium.database.tables.string_values import StringValues
from nylium.database.tables.integer_values import IntegerValues
from nylium.database.tables.numeric_values import NumericValues
from nylium.database.tables.boolean_values import BooleanValues
from nylium.database.tables.datetime_values import DatetimeValues
from nylium.database.tables.date_values import DateValues
from nylium.database.tables.time_values import TimeValues
from nylium.database.tables.monthday_values import MonthDayValues
from nylium.database.tables.monthdaytime_values import MonthDayTimeValues
from nylium.database.tables.enum_options import EnumOptions
from nylium.database.tables.unit_parts import UnitParts
from nylium.database.tables.instance_values import InstanceValues
from nylium.database.tables.array_values import ArrayValues
from nylium.database.tables.auth_users import AuthUsers
from nylium.database.tables.auth_credentials import AuthCredentials
from nylium.database.tables.auth_challenges import AuthChallenges
from nylium.database.tables.auth_sessions import AuthSessions
from nylium.database.tables.files import Files

__all__ = [
    "Base",
    "Types",
    "Props",
    "Instances",
    "StringValues",
    "IntegerValues",
    "NumericValues",
    "BooleanValues",
    "DatetimeValues",
    "DateValues",
    "TimeValues",
    "MonthDayValues",
    "MonthDayTimeValues",
    "EnumOptions",
    "UnitParts",
    "InstanceValues",
    "ArrayValues",
    "AuthUsers",
    "AuthCredentials",
    "AuthChallenges",
    "AuthSessions",
    "Files",
]
