"""Function tables — mapped Rows + their stores, one file per table (ADR-0033)."""
from nylium.table_rows.functions.function_edge import (
    FunctionEdge,
    FunctionEdges,
    function_edges,
)
from nylium.table_rows.functions.function_node import (
    FunctionNode,
    FunctionNodes,
    function_nodes,
)
from nylium.table_rows.functions.instance_function_link import (
    InstanceFunctionLink,
    InstanceFunctionLinks,
    instance_function_links,
)

__all__ = [
    "FunctionEdge",
    "FunctionEdges",
    "FunctionNode",
    "FunctionNodes",
    "InstanceFunctionLink",
    "InstanceFunctionLinks",
    "function_edges",
    "function_nodes",
    "instance_function_links",
]
