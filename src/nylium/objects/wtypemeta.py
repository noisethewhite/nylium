"""WTypeMeta: metaclass that materializes a WObject subclass into the
`types`/`props` tables at class-definition time, keeps the
type name -> python class registry for wrap(), and enforces link type
conformance at write time.

Dependency-inversion note: every layer below WObject (warray included)
needs *something* it can wrap links into, but importing WObject from
here would close an import cycle (WObject's metaclass is WTypeMeta).
So this module owns the abstraction instead: the WObjectShape protocol,
the StoredValue union built on it, and a registry slot for the WObject
root class, which the metaclass records when WObject itself is created.
WObject conforms structurally; nothing here imports it.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Protocol, TypeAlias, cast, get_args, get_origin
from uuid import UUID

from sqlalchemy.orm import Session

from nylium.database import Database
from nylium.database.tables import Instances
from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtype import WType

LIST_ANNOTATION_PREFIX = "list["
ABSTRACT_FLAG = "__abstract__"
PRIVATE_PREFIX = "_"
# annotationlib.Format.VALUE (PEP 649): evaluate __annotate_func__ to real objects.
# Mirrored as a constant instead of importing annotationlib, which only exists on 3.14+.
_ANNOTATE_FORMAT_VALUE = 1
WOBJECT_ROOT_NAME = "WObject"


class WObjectShape(Protocol):
    """The slice of WObject that lower layers are allowed to rely on."""

    @classmethod
    def wrap(cls, uuid: UUID) -> "WObjectShape": ...

    @property
    def uuid(self) -> UUID: ...


# The closed union of everything a prop can hold: scalar payloads,
# WObject links (structurally), (nested) lists of those. None means
# "never set". A string forward ref inside list[...] keeps the
# recursion parseable without typing.Union or the PEP 695 `type` stmt.
StoredValue: TypeAlias = ScalarPayload | WObjectShape | list["StoredValue"] | None


class WTypeMeta(type):
    _python_classes: ClassVar[dict[str, type[WObjectShape]]] = {}
    _root: ClassVar[type[WObjectShape] | None] = None

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        # object, not a domain union: a class namespace genuinely holds
        # arbitrary attributes (methods, annotations dict, flags). Any
        # would lie by permitting unchecked ops; object forces gates.
        namespace: dict[str, object],
        **kwargs: object,
    ):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        if name == WOBJECT_ROOT_NAME and mcls._root is None:
            mcls._root = cast(type[WObjectShape], cls)
        if namespace.get(ABSTRACT_FLAG):
            return cls
        mcls._python_classes[name] = cast(type[WObjectShape], cls)
        mcls._materialize(cast(type[WObjectShape], cls), namespace)
        return cls

    @classmethod
    def python_class(mcls, type_name: str) -> type[WObjectShape] | None:
        return mcls._python_classes.get(type_name)

    @classmethod
    def root(mcls) -> type[WObjectShape]:
        """The WObject base class itself. Registered when the metaclass
        created it; wrap() on it resolves registered subclasses."""
        if mcls._root is None:
            raise RuntimeError("WObject root requested before WObject was created")
        return mcls._root

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def check_link(mcls, session: Session, expected_name: str, value: object) -> None:
        root = mcls.root()
        if not isinstance(value, root):
            raise TypeError(
                f"{expected_name} prop takes a WObject, got {type(value).__name__}"
            )
        expected_cls = mcls.python_class(expected_name)
        if expected_cls is not None:
            if not isinstance(value, expected_cls):
                raise TypeError(
                    f"{expected_name} prop takes {expected_name}, got {type(value).__name__}"
                )
            return
        inst = session.get(Instances, value.uuid)
        actual = None if inst is None else WType.by_uuid(inst.type_uuid)
        if actual is None or actual.name != expected_name:
            raise TypeError(
                f"{expected_name} prop takes {expected_name}, got {'<missing instance>' if actual is None else actual.name}"
            )

    @classmethod
    @Database.sessionmethod(bundled=True, commit=True)
    def _materialize(mcls, cls: type[WObjectShape], namespace: dict[str, object]) -> None:
        WScalar.ensure_builtins()
        owner = WType.ensure(cls.__name__)
        for key, annotation in mcls._class_annotations(namespace).items():
            if key.startswith(PRIVATE_PREFIX):
                continue
            value_type = WType.ensure(mcls.resolve_annotation(annotation))
            _ = WProp.ensure(owner, key, value_type)

    @classmethod
    def resolve_annotation(mcls, annotation: object) -> str:
        if isinstance(annotation, str):
            return mcls._resolve_string_annotation(annotation)
        if get_origin(annotation) is list:
            element = mcls.resolve_annotation(cast(object, get_args(annotation)[0]))
            return WType.array_name(element)
        if isinstance(annotation, type) and issubclass(annotation, WScalar):
            return annotation.TYPE_NAME
        if isinstance(annotation, WTypeMeta):
            return annotation.__name__
        raise TypeError(
            f"unsupported prop annotation: {annotation!r}; props take WScalar subclasses, WObject subclasses or list[...] of those"
        )

    @classmethod
    def _class_annotations(mcls, namespace: dict[str, object]) -> dict[str, object]:
        # PEP 649 (3.14): annotations are lazy — the class namespace carries
        # `__annotate_func__` instead of the eager dict, and getattr(cls, "__annotations__")
        # during metaclass __new__ resolves to the PARENT's annotations. Read the dict
        # when present (<=3.13), otherwise evaluate __annotate_func__ in VALUE format.
        raw = namespace.get("__annotations__")
        if isinstance(raw, dict):
            return cast(dict[str, object], raw)
        annotate = namespace.get("__annotate_func__")
        if callable(annotate):
            annotate_fn = cast(Callable[[int], dict[str, object]], annotate)
            return dict(annotate_fn(_ANNOTATE_FORMAT_VALUE))
        return {}

    @classmethod
    def _resolve_string_annotation(mcls, annotation: str) -> str:
        name = annotation.strip().strip("\"'")
        if name.startswith(LIST_ANNOTATION_PREFIX) and name.endswith("]"):
            element = mcls.resolve_annotation(name[len(LIST_ANNOTATION_PREFIX) : -1])
            return WType.array_name(element)
        scalar = WScalar.by_class_name(name) or WScalar.by_type_name(name)
        if scalar is not None:
            return scalar.TYPE_NAME
        return name
