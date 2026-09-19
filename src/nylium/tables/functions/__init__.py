# Function-graph tables: nodes, edges and instance-level bindings (ADR-0029).
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.tables.functions.instance_function_links import TABLE_InstanceFunctionLinks

__all__ = [
    "TABLE_FunctionNodes",
    "TABLE_FunctionEdges",
    "TABLE_InstanceFunctionLinks",
]
