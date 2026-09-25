"""NyObject: the composed class — lifecycle + facade + attribute
machinery over the persistence mixin, materialized by NyTypeMeta."""
from __future__ import annotations

from typing import ClassVar

from nylium.ny.NyTypeMeta import NyTypeMeta
from nylium.ny.nyobject.AttrsMixin import AttrsMixin
from nylium.ny.nyobject.FacadeMixin import FacadeMixin
from nylium.ny.nyobject.LifecycleMixin import LifecycleMixin
from nylium.uuid import ObjectUUID


class NyObject(LifecycleMixin, FacadeMixin, AttrsMixin, metaclass=NyTypeMeta):
    __abstract__: ClassVar[bool] = True

    _uuid: ObjectUUID
