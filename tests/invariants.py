"""Objective invariants for query plans."""

from __future__ import annotations

from optimizer.plan import Plan
from optimizer.query import Query, connected


def assert_plan_invariants(plan: Plan, query: Query) -> None:
    assert isinstance(plan.join_order, tuple)
    assert set(plan.join_order) == set(query.tables)
    assert plan.estimated_cost >= 0
    assert plan.audit["selectivity"] == 0.1
    assert plan.audit["plans_explored"] >= 1

    joined = {plan.join_order[0]}
    for table in plan.join_order[1:]:
        assert any(connected(table, other, query.joins) for other in joined)
        joined.add(table)
