# Tables live in submodules by concern: values/ (prop-value tables),
# auth/ (users, credentials, sessions, tokens), functions/ (function graph),
# decor/ (type/trait decorators); base.py and files.py stay at the package
# root. This package keeps the flat import surface for the mapped classes,
# named TABLE_<Name>. The domain-object tables (types, instances, props,
# enum/unit params) moved to nylium.objects.tables / nylium.objects.rows
# (ADR-0019 domain/object split) — import those from there.
from nylium.tables.base import reg
from nylium.tables.values.string_values import TABLE_StringValues
from nylium.tables.values.integer_values import TABLE_IntegerValues
from nylium.tables.values.numeric_values import TABLE_NumericValues
from nylium.tables.values.boolean_values import TABLE_BooleanValues
from nylium.tables.values.datetime_values import TABLE_DatetimeValues
from nylium.tables.values.date_values import TABLE_DateValues
from nylium.tables.values.time_values import TABLE_TimeValues
from nylium.tables.values.monthday_values import TABLE_MonthDayValues
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues
from nylium.tables.values.instance_values import TABLE_InstanceValues
from nylium.tables.values.array_values import TABLE_ArrayValues
from nylium.tables.auth.auth_users import AuthUser, auth_users
from nylium.tables.auth.auth_credentials import AuthCredential, auth_credentials
from nylium.tables.auth.auth_challenges import AuthChallenge, auth_challenges
from nylium.tables.auth.auth_sessions import AuthSession, auth_sessions
from nylium.tables.auth.api_tokens import ApiToken, api_tokens
from nylium.tables.files import TABLE_Files, files
from nylium.tables.decor import (
    TABLE_TraitDecor,
    TABLE_TypeDecor,
    trait_decor,
    type_decor,
)
from nylium.tables.values.file_values import TABLE_FileValues
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.tables.functions.instance_function_links import TABLE_InstanceFunctionLinks

__all__ = [
    "reg",
    "files",
    "TABLE_StringValues",
    "TABLE_IntegerValues",
    "TABLE_NumericValues",
    "TABLE_BooleanValues",
    "TABLE_DatetimeValues",
    "TABLE_DateValues",
    "TABLE_TimeValues",
    "TABLE_MonthDayValues",
    "TABLE_MonthDayTimeValues",
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
    "TABLE_TypeDecor",
    "TABLE_TraitDecor",
    "type_decor",
    "trait_decor",
    "TABLE_FunctionNodes",
    "TABLE_FunctionEdges",
    "TABLE_InstanceFunctionLinks",
]
