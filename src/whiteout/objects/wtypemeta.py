"""WTypeMeta: metaclass that materializes a WObject subclass into the
`types`/`props` tables at class-definition time and keeps the
type name -> python class registry for wrap()."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast, get_args, get_origin

from whiteout.objects.scalars import scalars
from whiteout.objects.sessions import sessions
from whiteout.objects.wtype import WType

if TYPE_CHECKING:
    from whiteout.objects.wobject import WObject

LIST_ANNOTATION_PREFIX = "list["
ABSTRACT_FLAG = "__abstract__"
PRIVATE_PREFIX = "_"


class WTypeMeta(type):
    _python_classes: dict[str, "type[WObject]"] = {}

    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        if namespace.get(ABSTRACT_FLAG):
            return cls
        typed_cls = cast("type[WObject]", cls)
        mcls._python_classes[name] = typed_cls
        mcls._materialize(typed_cls)
        return cls

    @classmethod
    def python_class(mcls, type_name: str) -> "type[WObject] | None":
        return mcls._python_classes.get(type_name)

    @classmethod
    def _materialize(mcls, cls: "type[WObject]") -> None:
        with sessions.new() as session, session.begin():
            scalars.ensure_builtins(session)
            owner = WType.ensure(session, cls.__name__)
            for key, annotation in getattr(cls, "__annotations__", {}).items():
                if key.startswith(PRIVATE_PREFIX):
                    continue
                value_type = WType.ensure(session, mcls.resolve_annotation(annotation))
                owner.ensure_prop(session, key, value_type)

    @classmethod
    def resolve_annotation(mcls, annotation: object) -> str:
        if isinstance(annotation, str):
            return mcls._resolve_string_annotation(annotation)
        if get_origin(annotation) is list:
            element = mcls.resolve_annotation(get_args(annotation)[0])
            return WType.array_name(element)
        scalar_name = scalars.name_for_python_type(annotation)
        if scalar_name is not None:
            return scalar_name
        if isinstance(annotation, WTypeMeta):
            return annotation.__name__
        raise TypeError(f"unsupported annotation: {annotation!r}")

    @classmethod
    def _resolve_string_annotation(mcls, annotation: str) -> str:
        name = annotation.strip().strip("\"'")
        if name.startswith(LIST_ANNOTATION_PREFIX) and name.endswith("]"):
            element = mcls.resolve_annotation(name[len(LIST_ANNOTATION_PREFIX) : -1])
            return WType.array_name(element)
        return scalars.name_for_python_type_name(name) or name
