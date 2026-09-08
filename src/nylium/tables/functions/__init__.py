# Function-graph tables: nodes, edges and materialized dependencies.
from nylium.tables.functions.function_nodes import TABLE_FunctionNodes
from nylium.tables.functions.function_edges import TABLE_FunctionEdges
from nylium.tables.functions.function_deps import TABLE_FunctionDeps

__all__ = [
    "TABLE_FunctionNodes",
    "TABLE_FunctionEdges",
    "TABLE_FunctionDeps",
]
