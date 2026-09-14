"""WObject: the composed class — lifecycle + facade + attribute
machinery over the persistence mixin, materialized by WTypeMeta."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.objects.wtypemeta import WTypeMeta
from nylium.objects.wobject.attrs import AttrsMixin
from nylium.objects.wobject.facade import FacadeMixin
from nylium.objects.wobject.lifecycle import LifecycleMixin


class WObject(LifecycleMixin, FacadeMixin, AttrsMixin, metaclass=WTypeMeta):
    __abstract__: ClassVar[bool] = True

    _uuid: UUID
