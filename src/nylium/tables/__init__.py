# One file per table; this package keeps the flat import surface for the
# mapped classes, named TABLE_<Name>. The `types` store (ADR-0010) is the
# public entry point for type access; TABLE_Types is imported explicitly
# where a SQL join needs the mapped class.
from nylium.tables.base import Base
from nylium.tables.types import types
from nylium.tables.props import TABLE_Props, props
from nylium.tables.instances import TABLE_Instances, instances
from nylium.tables.string_values import TABLE_StringValues
from nylium.tables.integer_values import TABLE_IntegerValues
from nylium.tables.numeric_values import TABLE_NumericValues
from nylium.tables.boolean_values import TABLE_BooleanValues
from nylium.tables.datetime_values import TABLE_DatetimeValues
from nylium.tables.date_values import TABLE_DateValues
from nylium.tables.time_values import TABLE_TimeValues
from nylium.tables.monthday_values import TABLE_MonthDayValues
from nylium.tables.monthdaytime_values import TABLE_MonthDayTimeValues
from nylium.tables.enum_options import TABLE_EnumOptions, enum_options
from nylium.tables.unit_parts import TABLE_UnitParts, unit_parts
from nylium.tables.instance_values import TABLE_InstanceValues
from nylium.tables.array_values import TABLE_ArrayValues
from nylium.tables.auth_users import AuthUser, auth_users
from nylium.tables.auth_credentials import AuthCredential, auth_credentials
from nylium.tables.auth_challenges import AuthChallenge, auth_challenges
from nylium.tables.auth_sessions import AuthSession, auth_sessions
from nylium.tables.api_tokens import ApiToken, api_tokens
from nylium.tables.files import TABLE_Files, files
from nylium.tables.file_values import TABLE_FileValues
from nylium.tables.function_nodes import TABLE_FunctionNodes
from nylium.tables.function_edges import TABLE_FunctionEdges
from nylium.tables.function_deps import TABLE_FunctionDeps

__all__ = [
    "Base",
    "types",
    "instances",
    "props",
    "files",
    "enum_options",
    "unit_parts",
    "TABLE_Props",
    "TABLE_Instances",
    "TABLE_StringValues",
    "TABLE_IntegerValues",
    "TABLE_NumericValues",
    "TABLE_BooleanValues",
    "TABLE_DatetimeValues",
    "TABLE_DateValues",
    "TABLE_TimeValues",
    "TABLE_MonthDayValues",
    "TABLE_MonthDayTimeValues",
    "TABLE_EnumOptions",
    "TABLE_UnitParts",
    "TABLE_InstanceValues",
    "TABLE_ArrayValues",
    "AuthUser",
    "AuthCredential",
    "AuthChallenge",
    "AuthSession",
    "ApiToken",
    "auth_users",
    "auth_credentials",
    "auth_challenges",
    "auth_sessions",
    "api_tokens",
    "TABLE_Files",
    "TABLE_FileValues",
    "TABLE_FunctionNodes",
    "TABLE_FunctionEdges",
    "TABLE_FunctionDeps",
]
