"""Hidden edge-case tests for planner robustness."""

from __future__ import annotations

import pytest

from helpers import load_planner
from optimizer.catalog import TableStats
from optimizer.query import JoinPredicate, Query


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_equal_cost_tie_breaks_deterministically(planner):
    query = Query(
        tables=("x", "y"),
        joins=(JoinPredicate("x", "k", "y", "k"),),
    )
    catalog = {
        "x": TableStats("x", 100, 1.0),
        "y": TableStats("y", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert plan.estimated_cost == pytest.approx(1200.0)
    assert plan.join_order == ("x", "y")


def test_single_table_scan_only(planner):
    query = Query(tables=("solo",), joins=())
    catalog = {"solo": TableStats("solo", 42, 3.0)}
    plan = planner.plan_query(query, catalog)
    assert plan.join_order == ("solo",)
    assert plan.estimated_cost == pytest.approx(126.0)
    assert plan.audit["plans_explored"] == 1


def test_high_selectivity_trap_would_undercost_intermediate_joins(planner):
    """Using selectivity 1.0 would under-estimate cost vs the 0.1 contract."""
    query = Query(
        tables=("g1", "g2"),
        joins=(JoinPredicate("g1", "k", "g2", "k"),),
    )
    catalog = {"g1": TableStats("g1", 500, 1.0), "g2": TableStats("g2", 500, 1.0)}
    plan = planner.plan_query(query, catalog)
    wrong_selectivity_cost = (
        catalog["g1"].row_count * catalog["g1"].scan_cost_per_row
        + catalog["g2"].row_count * catalog["g2"].scan_cost_per_row
        + 500 * 500 * 1.0
    )
    assert plan.estimated_cost < wrong_selectivity_cost
