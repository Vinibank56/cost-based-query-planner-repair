"""Cost-based query planner (broken seed ? repair required)."""

from __future__ import annotations

from optimizer.catalog import TableStats
from optimizer.cost import scan_cost
from optimizer.plan import Plan
from optimizer.query import Query

# BUG: should use DEFAULT_SELECTIVITY (0.1) from cost.py
_BROKEN_SELECTIVITY = 1.0


def plan_query(query: Query, catalog: dict[str, TableStats]) -> Plan:
    """Select a join order ? seed implementation is incorrect."""
    for table in query.tables:
        if table not in catalog:
            raise ValueError(f"unknown table: {table}")

    # BUG: alphabetical order only; no permutation search or connectivity check
    order = tuple(sorted(query.tables))

    rows = catalog[order[0]].row_count
    # BUG: skips scan cost for the first table in the join order
    total = 0.0

    for table in order[1:]:
        stats = catalog[table]
        total += scan_cost(stats)
        # BUG: additive join cost instead of left_rows * right_rows * selectivity
        total += rows + stats.row_count
        # BUG: additive row growth instead of multiplicative selectivity model
        rows = rows + stats.row_count

    return Plan(
        join_order=order,
        estimated_cost=total,
        audit={
            "plans_explored": 1,
            "selectivity": _BROKEN_SELECTIVITY,
            "algorithm": "left_deep_permutation",
        },
    )
