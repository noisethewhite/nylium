"""Markdown export of an object view — human-readable, link-preserving.

Links to other objects render as markdown links whose href carries the
target uuid (`object:<uuid>`), so the pointer survives a round trip while
the text stays readable. Nothing is expanded recursively: a graph is not
a tree, and inlining linked objects invites cycles and bloat.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from nylium.objects.wobject import ObjectView
from nylium.objects.wobject import (
    ArrayValue,
    EmbeddedValue,
    ObjectRef,
    PropValue,
    RefValue,
    ScalarValue,
)

NAME_PROP_KEY = "name"

_UNSET = "—"
_EMPTY_ARRAY = "∅"


class MarkdownRenderer:
    """Render one object view as a markdown document.

    `ref_label` resolves a link target's display name — the caller supplies
    it because only the object layer can read a linked instance's `name`
    prop.
    """

    def __init__(self, ref_label: Callable[[ObjectRef], str]) -> None:
        self._ref_label: Callable[[ObjectRef], str] = ref_label

    def render(self, view: ObjectView) -> tuple[str, str]:
        """Return (filename, content) for the object markdown document."""
        title = self._title(view)
        lines: list[str] = [f"# {view.type_name}: {title}", ""]
        for key, value in view.props.items():
            lines.append(f"- **{key}**: {self._render_prop(value)}")
        return f"{self._slug(title)}.md", "\n".join(lines) + "\n"

    def _title(self, view: ObjectView) -> str:
        name = view.props.get(NAME_PROP_KEY)
        if isinstance(name, ScalarValue) and name.value is not None:
            return str(name.value)
        return str(view.uuid)

    def _slug(self, text: str) -> str:
        slug = re.sub(r"[^0-9A-Za-z_-]+", "-", text).strip("-")
        return slug or "object"

    def _render_prop(self, value: PropValue, indent: str = "") -> str:
        if isinstance(value, ScalarValue):
            return self._render_scalar(value)
        if isinstance(value, RefValue):
            if value.ref is None:
                return _UNSET
            return f"[{self._ref_label(value.ref)}](object:{value.ref.uuid})"
        if isinstance(value, ArrayValue):
            return self._render_array(value, indent)
        return self._render_embedded(value, indent)

    def _render_scalar(self, value: ScalarValue) -> str:
        if value.value is None:
            return _UNSET
        if value.unit is not None:
            return f"{value.value} {value.unit}"
        return str(value.value)

    def _render_array(self, value: ArrayValue, indent: str) -> str:
        if value.items is None:
            return _UNSET
        if not value.items:
            return _EMPTY_ARRAY
        rows = [
            f"{indent}  - {self._render_prop(item, indent + '  ')}"
            for item in value.items
        ]
        return "\n" + "\n".join(rows)

    def _render_embedded(self, value: EmbeddedValue, indent: str) -> str:
        if not value.props:
            return _UNSET
        rows = [
            f"{indent}  - **{key}**: {self._render_prop(prop, indent + '  ')}"
            for key, prop in value.props.items()
        ]
        return "\n" + "\n".join(rows)
