"""NyObject: the composed class — lifecycle + facade + attribute
machinery over the persistence mixin, materialized by NyTypeMeta."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.objects.nytypemeta import NyTypeMeta
from nylium.objects.nyobject.AttrsMixin import AttrsMixin
from nylium.objects.nyobject.FacadeMixin import FacadeMixin
from nylium.objects.nyobject.LifecycleMixin import LifecycleMixin


class NyObject(LifecycleMixin, FacadeMixin, AttrsMixin, metaclass=NyTypeMeta):
    __abstract__: ClassVar[bool] = True

    _uuid: UUID
