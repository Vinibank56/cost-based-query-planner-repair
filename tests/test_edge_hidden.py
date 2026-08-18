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
