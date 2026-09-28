"""Dynamic object layer over database/tables.py.

Ny-классы — доменные фасады над таблицами: NyObject (экземпляры),
NyType (схема), NyProp (свойства), NyScalar и семейство (скаляры),
NyFormula/NyFunction (вычисляемые пропы, ADR-0005/0007), NyEnum, NyFile,
NyArray, NyEmbedded, NyUnit. Семантику несёт слой: SQL живёт только в
tables/ и database/ (ADR-0019). Value-типы (Quantity, MonthDay,
MonthDayTime) — в ``nylium.data.types``; wire DTO — в ``nylium.data.views``.

Крупные фасады — пакеты (nyobject/, nyformula/, nyfunction/ — ADR-0018):
stateless-фасад = concern-модули + @final класс со staticmethod-
биндингом. Мелкие семейства (nyscalar, monthday, quantity) остаются
одним файлом.

Порядок ре-экспорта значим: scalar/type фасады раньше, NyObject —
последним (он тянет nyobject/, который читает скаляры из ny по кругу).
"""
from nylium.ny.NyArray import NyArray
from nylium.ny.NyBoolean import NyBoolean
from nylium.ny.NyColor import NyColor
from nylium.ny.NyDate import NyDate
from nylium.ny.NyDatetime import NyDatetime
from nylium.ny.NyEmbedded import NyEmbedded
from nylium.ny.NyEnum import NyEnum
from nylium.ny.NyFile import NyFile
from nylium.ny.NyInteger import NyInteger
from nylium.ny.NyMonthDay import NyMonthDay
from nylium.ny.NyMonthDayTime import NyMonthDayTime
from nylium.ny.NyNumeric import NyNumeric
from nylium.ny.NyObjectProtocol import NyObjectProtocol
from nylium.ny.NyProp import NyProp
from nylium.ny.NyScalar import NyScalar, ScalarPayload
from nylium.ny.NyString import NyString
from nylium.ny.NyTime import NyTime
from nylium.ny.NyType import NyType
from nylium.ny.NyTypeMeta import NyTypeMeta, StoredValue
from nylium.ny.NyUnit import NyUnit
from nylium.ny.nyobject.NyObject import NyObject

__all__ = [
    "NyArray",
    "NyBoolean",
    "NyColor",
    "NyDate",
    "NyDatetime",
    "NyEmbedded",
    "NyEnum",
    "NyFile",
    "NyInteger",
    "NyMonthDay",
    "NyMonthDayTime",
    "NyNumeric",
    "NyObject",
    "NyObjectProtocol",
    "NyProp",
    "NyScalar",
    "NyString",
    "NyTime",
    "NyType",
    "NyTypeMeta",
    "NyUnit",
    "ScalarPayload",
    "StoredValue",
]
