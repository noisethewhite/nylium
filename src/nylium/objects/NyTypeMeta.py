"""NyTypeMeta: metaclass that materializes a NyObject subclass into the
`types`/`props` tables at class-definition time, keeps the
type name -> python class registry for wrap(), and enforces link type
conformance at write time.

Dependency-inversion note: every layer below NyObject (nyarray included)
needs *something* it can wrap links into, but importing NyObject from
here would close an import cycle (NyObject's metaclass is NyTypeMeta).
So this module owns the abstraction instead: the NyObjectShape protocol,
the StoredValue union built on it, and a registry slot for the NyObject
root class, which the metaclass records when NyObject itself is created.
NyObject conforms structurally; nothing here imports it.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, TypeAlias, cast, get_args, get_origin
from uuid import UUID

from nylium.database import Database
from nylium.data.tables import instances
from nylium.data.tables import Traits
from nylium.data.tables import TypeTraits
from nylium.objects.Quantity import Quantity
from nylium.objects.NyProp import NyProp
from nylium.objects.NyScalar import NyScalar
from nylium.objects.NyScalar import ScalarPayload
from nylium.objects.NyType import NyType
from nylium.objects.NyObjectShape import NyObjectShape

LIST_ANNOTATION_PREFIX = "list["
ABSTRACT_FLAG = "__abstract__"
PRIVATE_PREFIX = "_"
# annotationlib.Format.VALUE (PEP 649): evaluate __annotate_func__ to real objects.
# Mirrored as a constant instead of importing annotationlib, which only exists on 3.14+.
_ANNOTATE_FORMAT_VALUE = 1
NYOBJECT_ROOT_NAME = "NyObject"




# The closed union of everything a prop can hold: scalar payloads,
# unit-aware quantities, NyObject links (structurally), (nested) lists of
# those. None means "never set". A string forward ref inside list[...]
# keeps the recursion parseable without typing.Union or the PEP 695
# `type` stmt.
# dict[str, StoredValue] is the write-side-only draft for embedded
# (composition) props, ADR-0004 — reads always come back as NyObject
# links, the dict never leaves the write path.
StoredValue: TypeAlias = (
    ScalarPayload | Quantity | NyObjectShape | UUID | list["StoredValue"] | dict[str, "StoredValue"] | None
)


class NyTypeMeta(type):
    _python_classes: ClassVar[dict[str, type[NyObjectShape]]] = {}
    _root: ClassVar[type[NyObjectShape] | None] = None

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
        if name == NYOBJECT_ROOT_NAME and mcls._root is None:
            mcls._root = cast(type[NyObjectShape], cls)
        if namespace.get(ABSTRACT_FLAG):
            return cls
        mcls._python_classes[name] = cast(type[NyObjectShape], cls)
        mcls._materialize(cast(type[NyObjectShape], cls), namespace)
        return cls

    @classmethod
    def python_class(mcls, type_name: str) -> type[NyObjectShape] | None:
        return mcls._python_classes.get(type_name)

    @classmethod
    def root(mcls) -> type[NyObjectShape]:
        """The NyObject base class itself. Registered when the metaclass
        created it; wrap() on it resolves registered subclasses."""
        if mcls._root is None:
            raise RuntimeError("NyObject root requested before NyObject was created")
        return mcls._root

    @classmethod
    @Database.use_same_session
    def check_link(mcls, expected_name: str, value: object) -> None:
        root = mcls.root()
        if not isinstance(value, root):
            raise TypeError(
                f"{expected_name} prop takes a NyObject, got {type(value).__name__}"
            )
        expected_cls = mcls.python_class(expected_name)
        if expected_cls is not None:
            if not isinstance(value, expected_cls):
                raise TypeError(
                    f"{expected_name} prop takes {expected_name}, got {type(value).__name__}"
                )
            return
        inst = instances.get(value.uuid)
        actual = None if inst is None else NyType.by_uuid(inst.type_uuid)
        if actual is None or actual.name != expected_name:
            raise TypeError(
                f"{expected_name} prop takes {expected_name}, got {'<missing instance>' if actual is None else actual.name}"
            )
        if actual.is_embedded:
            raise TypeError(
                f"{expected_name} is embedded (ADR-0004) — link it from its owner only, as an inline props draft"
            )

    @classmethod
    @Database.use_same_session
    def check_trait_link(mcls, trait_name: str, value: object) -> None:
        """ADR-0013: an Any<TraitName> prop accepts a link to any object
        whose *type* carries the trait. Embedded targets are rejected just
        like plain links."""
        root = mcls.root()
        if not isinstance(value, root):
            raise TypeError(
                f"Any<{trait_name}> prop takes a NyObject, got {type(value).__name__}"
            )
        inst = instances.get(value.uuid)
        actual = None if inst is None else NyType.by_uuid(inst.type_uuid)
        if actual is None:
            raise TypeError(
                f"Any<{trait_name}> prop takes an object with trait {trait_name!r}, got <missing instance>"
            )
        if actual.is_embedded:
            raise TypeError(
                f"Any<{trait_name}> target {actual.name!r} is embedded (ADR-0004) — link it from its owner only"
            )
        trait_uuid = Traits.uuid_by_name(trait_name)
        if not TypeTraits.is_attached(actual.uuid, trait_uuid):
            raise TypeError(
                f"Any<{trait_name}> prop takes an object with trait {trait_name!r}, got {actual.name!r}"
            )

    @classmethod
    @Database.commit_after_this
    def _materialize(mcls, cls: type[NyObjectShape], namespace: dict[str, object]) -> None:
        NyScalar.ensure_builtins()
        owner = NyType.ensure(cls.__name__)
        for key, annotation in mcls._class_annotations(namespace).items():
            if key.startswith(PRIVATE_PREFIX):
                continue
            value_type = NyType.ensure(mcls.resolve_annotation(annotation))
            _ = NyProp.ensure(owner, key, value_type)

    @classmethod
    def resolve_annotation(mcls, annotation: object) -> str:
        if isinstance(annotation, str):
            return mcls._resolve_string_annotation(annotation)
        if get_origin(annotation) is list:
            element = mcls.resolve_annotation(cast(object, get_args(annotation)[0]))
            return NyType.array_name(element)
        if isinstance(annotation, type) and issubclass(annotation, NyScalar):
            return annotation.TYPE_NAME
        if isinstance(annotation, NyTypeMeta):
            return annotation.__name__
        raise TypeError(
            f"unsupported prop annotation: {annotation!r}; props take NyScalar subclasses, NyObject subclasses or list[...] of those"
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
            return NyType.array_name(element)
        scalar = NyScalar.by_class_name(name) or NyScalar.by_type_name(name)
        if scalar is not None:
            return scalar.TYPE_NAME
        return name
