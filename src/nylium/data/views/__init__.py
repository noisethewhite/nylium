"""Wire DTOs (ADR-0011 §5): values, tags, and object/type/function views.

One class per file, re-exported here so call sites address them as
``nylium.data.views.<Name>`` regardless of the domain module.
"""
from nylium.data.views.ArrayValueView import ArrayValueView
from nylium.data.views.EmbeddedValueView import EmbeddedValueView
from nylium.data.views.EnumOptionView import EnumOptionView
from nylium.data.views.FileView import FileView
from nylium.data.views.FunctionEdgeView import FunctionEdgeView
from nylium.data.views.FunctionNodeView import FunctionNodeView
from nylium.data.views.FunctionView import FunctionView
from nylium.data.views.ObjectRefView import ObjectRefView
from nylium.data.views.ObjectView import ObjectView
from nylium.data.views.PropView import PropView
from nylium.data.views.RefValueView import RefValueView
from nylium.data.views.ScalarValueView import ScalarValueView
from nylium.data.views.StorageStats import StorageStats
from nylium.data.views.TagView import TagView
from nylium.data.views.TraitView import TraitView
from nylium.data.views.TypeView import TypeView
from nylium.data.views.UnitPartView import UnitPartView
from nylium.data.views.values import PropValue

__all__ = [
    "ArrayValueView",
    "EmbeddedValueView",
    "EnumOptionView",
    "FileView",
    "FunctionEdgeView",
    "FunctionNodeView",
    "FunctionView",
    "ObjectRefView",
    "ObjectView",
    "PropValue",
    "PropView",
    "RefValueView",
    "ScalarValueView",
    "StorageStats",
    "TagView",
    "TraitView",
    "TypeView",
    "UnitPartView",
]
