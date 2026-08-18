"""Visible verifier cases documented in instruction.md."""

from __future__ import annotations

import pytest

from helpers import load_planner, sample_catalog, star_three_table_query
from invariants import assert_plan_invariants
from optimizer.parser import parse_simple_sql


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_plan_result_shape(planner):
    plan = planner.plan_query(star_three_table_query(), sample_catalog())
    assert hasattr(plan, "join_order")
    assert hasattr(plan, "estimated_cost")
    assert set(plan.audit.keys()) >= {"plans_explored", "selectivity", "algorithm"}


def test_three_table_star_selects_minimum_cost_order(planner):
    plan = planner.plan_query(star_three_table_query(), sample_catalog())
    assert plan.join_order == ("orders", "products", "customers")
    assert plan.estimated_cost == pytest.approx(511600.0)
    assert plan.audit["plans_explored"] == 4
    assert_plan_invariants(plan, star_three_table_query())


def test_two_table_join_cost(planner):
    from optimizer.catalog import TableStats
    from optimizer.query import JoinPredicate, Query

    query = Query(
        tables=("orders", "customers"),
        joins=(JoinPredicate("orders", "customer_id", "customers", "id"),),
    )
    catalog = {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    assert plan.estimated_cost == pytest.approx(51500.0)
    assert plan.audit["plans_explored"] == 2


def test_sql_parse_and_plan(planner):
    sql = (
        "SELECT * FROM orders, customers, products "
        "WHERE orders.customer_id = customers.id AND orders.product_id = products.id"
    )
    query = parse_simple_sql(sql)
    plan = planner.plan_query(query, sample_catalog())
    assert plan.estimated_cost == pytest.approx(511600.0)


def test_rejects_unknown_table(planner):
    from optimizer.query import Query

    query = Query(tables=("missing",), joins=())
    with pytest.raises(ValueError, match="unknown table"):
        planner.plan_query(query, sample_catalog())
