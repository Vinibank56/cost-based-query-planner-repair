"""Hidden behavioral property tests."""

from __future__ import annotations

import pytest

from helpers import load_planner, star_three_table_query
from optimizer.catalog import TableStats
from optimizer.query import JoinPredicate, Query


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_smallest_table_first_not_always_optimal(planner):
    """Anti-greedy: alphabetical/smallest-first order is suboptimal on star query."""
    plan = planner.plan_query(star_three_table_query(), {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    })
    assert plan.join_order[0] != "customers"


def test_explores_more_than_one_plan_on_star(planner):
    plan = planner.plan_query(star_three_table_query(), {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    })
    assert plan.audit["plans_explored"] >= 4


def test_cost_uses_default_selectivity(planner):
    plan = planner.plan_query(star_three_table_query(), {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    })
    assert plan.audit["selectivity"] == pytest.approx(0.1)


def test_join_order_is_connected(planner):
    query = Query(
        tables=("r", "s", "t"),
        joins=(
            JoinPredicate("r", "id", "s", "id"),
            JoinPredicate("s", "id", "t", "id"),
        ),
    )
    catalog = {n: TableStats(n, 100, 1.0) for n in "rst"}
    plan = planner.plan_query(query, catalog)
    joined = {plan.join_order[0]}
    for table in plan.join_order[1:]:
        assert table in {"r", "s", "t"}
        joined.add(table)
