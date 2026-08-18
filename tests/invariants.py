"""Objective invariants for query plans."""

from __future__ import annotations

import itertools

from optimizer.catalog import TableStats
from optimizer.plan import Plan
from optimizer.query import Query, connected
from spec_reference import _is_valid_join_order, recompute_left_deep_cost


def assert_plan_invariants(plan: Plan, query: Query) -> None:
    assert isinstance(plan.join_order, tuple)
    assert set(plan.join_order) == set(query.tables)
    assert plan.estimated_cost >= 0
    assert plan.audit["selectivity"] == 0.1
    assert plan.audit["plans_explored"] >= 1
    assert plan.audit["algorithm"] == "left_deep_permutation"

    joined = {plan.join_order[0]}
    for table in plan.join_order[1:]:
        assert any(connected(table, other, query.joins) for other in joined)
        joined.add(table)


def assert_minimum_cost_plan(
    plan: Plan, query: Query, catalog: dict[str, TableStats]
) -> None:
    """Returned plan must be no more expensive than any other valid order."""
    assert_plan_invariants(plan, query)
    best = plan.estimated_cost
    for perm in itertools.permutations(query.tables):
        if not _is_valid_join_order(perm, query):
            continue
        cost = recompute_left_deep_cost(perm, catalog)
        assert best <= cost + 1e-6
    assert plan.estimated_cost == recompute_left_deep_cost(plan.join_order, catalog)
