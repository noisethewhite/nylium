"""WFunction static node typing (ADR-0007): the kind -> arity whitelist
and the per-kind output-type / input-conformance rules. Pure static
logic — no graph rows are read here."""
from __future__ import annotations

from collections.abc import Mapping

from nylium.objects.wprop import WProp
from nylium.objects.wscalar import WInteger, WNumeric, WScalar, WString
from nylium.objects.wtype import WType
from nylium.objects.wfunction.constants import (
    NODE_ADD,
    NODE_AVERAGE,
    NODE_CAST,
    NODE_CONST,
    NODE_COUNT,
    NODE_DIV,
    NODE_GET_PROP,
    NODE_MAP,
    NODE_MAX,
    NODE_MIN,
    NODE_MUL,
    NODE_SUB,
    NODE_SUM,
    NUMERIC_SCALARS,
    NodeType,
    fail,
    is_array_type,
    is_numeric_scalar,
)

# kind -> input arity. validate_graph rejects any kind missing here, so
# this table IS the node whitelist.
NODE_ARITY: dict[str, int] = {
    NODE_GET_PROP: 0,
    NODE_CONST: 0,
    NODE_ADD: 2,
    NODE_SUB: 2,
    NODE_MUL: 2,
    NODE_DIV: 2,
    NODE_SUM: 1,
    NODE_AVERAGE: 1,
    NODE_COUNT: 1,
    NODE_MIN: 1,
    NODE_MAX: 1,
    NODE_CAST: 1,
    NODE_MAP: 1,
}


def node_output_type(
    kind: str,
    config: Mapping[str, object],
    input_type: str,
    input_types: list[NodeType],
) -> NodeType:
    """The static output type of a node, given the function's input
    type `T` (for `get_prop` lookups) and the node's config."""
    if kind == NODE_GET_PROP:
        key = config.get("key")
        if not isinstance(key, str):
            fail("get_prop needs a string 'key' in config")
        owner = WType.by_name(input_type)
        if owner is None:
            fail(f"cannot resolve function input type {input_type!r}")
        prop = WProp.by_key(owner, key)
        if prop is None:
            fail(f"get_prop references unknown prop {key!r} of {input_type}")
        value_name = prop.value_type().name
        if WScalar.by_type_name(value_name) is not None:
            return value_name
        if is_array_type(value_name):
            return value_name
        fail(
            f"get_prop can only read scalar or array props, got {value_name!r}"
        )
    if kind == NODE_MAP:
        key = config.get("key")
        if not isinstance(key, str):
            fail("map needs a string 'key' in config")
        array_type = input_types[0]
        if not is_array_type(array_type):
            fail(f"map needs an array input, got {array_type!r}")
        element = WType.element_name(array_type)
        owner = WType.by_name(element)
        if owner is None:
            fail(f"cannot resolve map element type {element!r}")
        prop = WProp.by_key(owner, key)
        if prop is None:
            fail(f"map references unknown prop {key!r} of {element}")
        value_name = prop.value_type().name
        if WScalar.by_type_name(value_name) is None and not is_array_type(value_name):
            fail(f"map can only read scalar or array props, got {value_name!r}")
        return WType.array_name(value_name)
    if kind == NODE_CONST:
        value = config.get("value")
        if isinstance(value, bool) or value is None:
            fail("const needs a number or string 'value'")
        if isinstance(value, int):
            return WInteger.TYPE_NAME
        if isinstance(value, (float, str)):
            return WNumeric.TYPE_NAME if isinstance(value, float) else WString.TYPE_NAME
        fail("const value must be an int, float or str")
    if kind in (NODE_ADD, NODE_SUB, NODE_MUL, NODE_DIV):
        return WNumeric.TYPE_NAME
    if kind in (NODE_SUM, NODE_AVERAGE, NODE_MIN, NODE_MAX):
        return WNumeric.TYPE_NAME
    if kind == NODE_COUNT:
        return WInteger.TYPE_NAME
    if kind == NODE_CAST:
        target = config.get("target")
        if not isinstance(target, str) or WScalar.by_type_name(target) is None:
            fail("cast needs a scalar 'target' in config")
        return target
    fail(f"unknown node kind {kind!r}")


def check_inputs(kind: str, input_types: list[NodeType]) -> None:
    """Type-conformance check on a node's resolved input types."""
    if kind in (NODE_ADD, NODE_SUB, NODE_MUL, NODE_DIV):
        for t in input_types:
            if not is_numeric_scalar(t):
                fail(f"{kind} needs numeric inputs, got {t!r}")
        return
    if kind in (NODE_SUM, NODE_AVERAGE, NODE_MIN, NODE_MAX):
        array_type = input_types[0]
        if not is_array_type(array_type):
            fail(f"{kind} needs an array input, got {array_type!r}")
        element = WType.element_name(array_type)
        if not is_numeric_scalar(element):
            fail(f"{kind} needs a numeric array, got Array<{element}>")
        return
    if kind == NODE_COUNT:
        if not is_array_type(input_types[0]):
            fail(f"count needs an array input, got {input_types[0]!r}")
        return
    if kind == NODE_CAST:
        src = input_types[0]
        if src not in NUMERIC_SCALARS and src != WString.TYPE_NAME:
            fail(f"cast needs a numeric or string input, got {src!r}")
    if kind == NODE_MAP:
        array_type = input_types[0]
        if not is_array_type(array_type):
            fail(f"map needs an array input, got {array_type!r}")
        element = WType.element_name(array_type)
        if WScalar.by_type_name(element) is not None or WType.is_array_name(element):
            fail(f"map needs an array of objects, got Array<{element}>")
