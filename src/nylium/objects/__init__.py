"""Dynamic object layer over database/tables.py.

W*-классы — доменные фасады над таблицами: NyObject (экземпляры),
NyType (схема), NyProp (свойства), NyScalar и семейство (скаляры),
NyFormula/NyFunction (вычисляемые пропы, ADR-0005/0007), NyEnum, NyFile,
NyArray, NyEmbedded, NyUnit. Префикс W — исторический (wrapper), семантику
несёт слой: SQL живёт только в tables/ и database/ (ADR-0019).

Крупные фасады — пакеты (nyobject/, nyformula/, nyfunction/ — ADR-0018):
stateless-фасад = concern-модули + @final класс со staticmethod-
биндингом. Мелкие семейства (nyscalar, monthday, quantity) остаются
одним файлом.
"""
from nylium.objects.nyobject.NyObject import NyObject
from nylium.objects.nyprop import NyProp
from nylium.objects.nyscalar import (
    NyBoolean,
    NyDatetime,
    NyInteger,
    NyNumeric,
    NyScalar,
    NyString,
)
from nylium.objects.NyType import NyType
from nylium.objects.nytypemeta import NyTypeMeta

__all__ = [
    "NyBoolean",
    "NyDatetime",
    "NyInteger",
    "NyNumeric",
    "NyObject",
    "NyProp",
    "NyScalar",
    "NyString",
    "NyType",
    "NyTypeMeta",
]
