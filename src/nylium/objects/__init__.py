"""Dynamic object layer over database/tables.py.

W*-классы — доменные фасады над таблицами: WObject (экземпляры),
WType (схема), WProp (свойства), WScalar и семейство (скаляры),
WFormula/WFunction (вычисляемые пропы, ADR-0005/0007), WEnum, WFile,
WArray, WEmbedded, WUnit. Префикс W — исторический (wrapper), семантику
несёт слой: SQL живёт только в tables/ и database/ (ADR-0019).

Крупные фасады — пакеты (wobject/, wformula/, wfunction/ — ADR-0018):
stateless-фасад = concern-модули + @final класс со staticmethod-
биндингом. Мелкие семейства (wscalar, monthday, quantity) остаются
одним файлом.
"""
from nylium.objects.wobject.object import WObject
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import (
    WBoolean,
    WDatetime,
    WInteger,
    WNumeric,
    WScalar,
    WString,
)
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import WTypeMeta

__all__ = [
    "WBoolean",
    "WDatetime",
    "WInteger",
    "WNumeric",
    "WObject",
    "WProp",
    "WScalar",
    "WString",
    "WType",
    "WTypeMeta",
]
