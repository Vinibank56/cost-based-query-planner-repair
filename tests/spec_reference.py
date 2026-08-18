"""Canonical planner specification — sealed reference."""

from __future__ import annotations

import itertools

from optimizer.catalog import TableStats
from optimizer.cost import DEFAULT_SELECTIVITY, join_cost, output_rows, scan_cost
from optimizer.plan import Plan
from optimizer.query import Query, connected


def _is_valid_join_order(order: tuple[str, ...], query: Query) -> bool:
    if set(order) != set(query.tables):
        return False
    joined = {order[0]}
    for table in order[1:]:
        if not any(connected(table, other, query.joins) for other in joined):
            return False
        joined.add(table)
    return True


def _cost_for_order(order: tuple[str, ...], catalog: dict[str, TableStats]) -> float:
    first = order[0]
    rows = catalog[first].row_count
    total = scan_cost(catalog[first])
    for table in order[1:]:
        stats = catalog[table]
        total += scan_cost(stats)
        total += join_cost(rows, stats.row_count, DEFAULT_SELECTIVITY)
        rows = output_rows(rows, stats.row_count, DEFAULT_SELECTIVITY)
    return total


def plan_query_reference(query: Query, catalog: dict[str, TableStats]) -> Plan:
    for table in query.tables:
        if table not in catalog:
            raise ValueError(f"unknown table: {table}")

    best_order: tuple[str, ...] | None = None
    best_cost = float("inf")
    explored = 0

    for perm in itertools.permutations(query.tables):
        if not _is_valid_join_order(perm, query):
            continue
        explored += 1
        cost = _cost_for_order(perm, catalog)
        if cost < best_cost:
            best_cost = cost
            best_order = perm

    if best_order is None:
        raise ValueError("no valid join order for query graph")

    return Plan(
        join_order=best_order,
        estimated_cost=best_cost,
        audit={
            "plans_explored": explored,
            "selectivity": DEFAULT_SELECTIVITY,
            "algorithm": "left_deep_permutation",
        },
    )
