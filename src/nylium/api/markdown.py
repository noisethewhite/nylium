"""Markdown export of an object view — human-readable, link-preserving.

Links to other objects render as markdown links whose href carries the
target uuid (`object:<uuid>`), so the pointer survives a round trip while
the text stays readable. Nothing is expanded recursively: a graph is not
a tree, and inlining linked objects invites cycles and bloat.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from nylium.api.views import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    ObjectView,
    PropValue,
    RefValue,
    ScalarValue,
)

_UNSET = "—"
_EMPTY_ARRAY = "∅"
NAME_PROP_KEY = "name"


def render_object_markdown(
    view: ObjectView, ref_label: Callable[[ObjectRef], str]
) -> tuple[str, str]:
    """Render one object as a markdown document.

    Returns (filename, content). `ref_label` resolves a link target's
    display name — the caller supplies it because only the object layer
    can read a linked instance's `name` prop.
    """
    title = _title(view)
    lines: list[str] = [f"# {view.type_name}: {title}", ""]
    for key, value in view.props.items():
        lines.append(f"- **{key}**: {_render_prop(value, ref_label)}")
    return f"{_slug(title)}.md", "\n".join(lines) + "\n"


def _title(view: ObjectView) -> str:
    name = view.props.get(NAME_PROP_KEY)
    if isinstance(name, ScalarValue) and name.value is not None:
        return str(name.value)
    return str(view.uuid)


def _slug(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_-]+", "-", text).strip("-")
    return slug or "object"


def _render_prop(
    value: PropValue, ref_label: Callable[[ObjectRef], str], indent: str = ""
) -> str:
    if isinstance(value, ScalarValue):
        return _render_scalar(value)
    if isinstance(value, RefValue):
        if value.ref is None:
            return _UNSET
        return f"[{ref_label(value.ref)}](object:{value.ref.uuid})"
    if isinstance(value, ArrayValue):
        return _render_array(value, ref_label, indent)
    return _render_embedded(value, ref_label, indent)


def _render_scalar(value: ScalarValue) -> str:
    if value.value is None:
        return _UNSET
    if value.unit is not None:
        return f"{value.value} {value.unit}"
    return str(value.value)


def _render_array(
    value: ArrayValue, ref_label: Callable[[ObjectRef], str], indent: str
) -> str:
    if value.items is None:
        return _UNSET
    if not value.items:
        return _EMPTY_ARRAY
    rows = [
        f"{indent}  - {_render_prop(item, ref_label, indent + '  ')}"
        for item in value.items
    ]
    return "\n" + "\n".join(rows)


def _render_embedded(
    value: EmbeddedValue, ref_label: Callable[[ObjectRef], str], indent: str
) -> str:
    if not value.props:
        return _UNSET
    rows = [
        f"{indent}  - **{key}**: {_render_prop(prop, ref_label, indent + '  ')}"
        for key, prop in value.props.items()
    ]
    return "\n" + "\n".join(rows)
