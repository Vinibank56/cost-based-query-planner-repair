"""Hidden behavioral property tests."""

from __future__ import annotations

import pytest

from helpers import load_planner, sample_catalog, star_three_table_query
from invariants import assert_minimum_cost_plan, assert_plan_invariants
from optimizer.catalog import TableStats
from optimizer.query import JoinPredicate, Query, connected
from spec_reference import recompute_left_deep_cost


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_smallest_table_first_not_always_optimal(planner):
    """Anti-greedy: alphabetical/smallest-first order is suboptimal on star query."""
    query = star_three_table_query()
    catalog = {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert plan.join_order[0] != "customers"
    assert_minimum_cost_plan(plan, query, catalog)


def test_explores_more_than_one_plan_on_star(planner):
    query = star_three_table_query()
    catalog = {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert plan.audit["plans_explored"] >= 4


def test_cost_uses_default_selectivity(planner):
    query = star_three_table_query()
    catalog = {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
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
        assert any(connected(table, other, query.joins) for other in joined)
        joined.add(table)


def test_reported_cost_matches_stepwise_recomputation(planner):
    """Anti-stub: cost must equal manual left-deep accumulation for chosen order."""
    query = Query(
        tables=("a", "b", "c"),
        joins=(
            JoinPredicate("a", "x", "b", "x"),
            JoinPredicate("b", "y", "c", "y"),
        ),
    )
    catalog = {
        "a": TableStats("a", 1000, 1.0),
        "b": TableStats("b", 500, 1.0),
        "c": TableStats("c", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert plan.estimated_cost == pytest.approx(
        recompute_left_deep_cost(plan.join_order, catalog)
    )


def test_alphabetical_order_is_not_hardcoded_optimum(planner):
    """Anti-heuristic: sorted table names produce a costlier plan on chain queries."""
    query = Query(
        tables=("a", "b", "c"),
        joins=(
            JoinPredicate("a", "x", "b", "x"),
            JoinPredicate("b", "y", "c", "y"),
        ),
    )
    catalog = {
        "a": TableStats("a", 1000, 1.0),
        "b": TableStats("b", 500, 1.0),
        "c": TableStats("c", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    alphabetical_cost = recompute_left_deep_cost(("a", "b", "c"), catalog)
    assert plan.estimated_cost < alphabetical_cost


def test_distinct_catalogs_yield_distinct_costs(planner):
    """Anti-hardcode: changing cardinalities must change the optimized cost."""
    query = star_three_table_query()
    baseline = planner.plan_query(query, sample_catalog())
    shifted = planner.plan_query(
        query,
        {
            "orders": TableStats("orders", 5000, 1.0),
            "customers": TableStats("customers", 2500, 1.0),
            "products": TableStats("products", 500, 1.0),
        },
    )
    assert shifted.estimated_cost != pytest.approx(baseline.estimated_cost)
    assert shifted.estimated_cost > baseline.estimated_cost


def test_returned_plan_is_globally_minimum(planner):
    query = Query(
        tables=("hub", "leaf_a", "leaf_b"),
        joins=(
            JoinPredicate("hub", "id", "leaf_a", "id"),
            JoinPredicate("hub", "id", "leaf_b", "id"),
        ),
    )
    catalog = {
        "hub": TableStats("hub", 2000, 1.0),
        "leaf_a": TableStats("leaf_a", 80, 1.0),
        "leaf_b": TableStats("leaf_b", 320, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert_minimum_cost_plan(plan, query, catalog)
    assert_plan_invariants(plan, query)
