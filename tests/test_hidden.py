"""Held-out edge and correctness tests — sealed from agent."""

from __future__ import annotations

import pytest

from helpers import load_planner, sample_catalog
from invariants import assert_plan_invariants
from optimizer.catalog import TableStats
from optimizer.query import JoinPredicate, Query
from spec_reference import plan_query_reference


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_chain_join_optimal_order(planner):
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
    assert plan.join_order == ("b", "c", "a")
    assert plan.estimated_cost == pytest.approx(506600.0)
    assert_plan_invariants(plan, query)


def test_four_table_explores_multiple_plans(planner):
    query = Query(
        tables=("w", "x", "y", "z"),
        joins=(
            JoinPredicate("w", "a", "x", "a"),
            JoinPredicate("x", "b", "y", "b"),
            JoinPredicate("y", "c", "z", "c"),
        ),
    )
    catalog = {t: TableStats(t, 100 * (i + 1), 1.0) for i, t in enumerate("wxyz")}
    plan = planner.plan_query(query, catalog)
    assert plan.audit["plans_explored"] == 8
    assert plan.estimated_cost == pytest.approx(2463000.0)


@pytest.mark.parametrize(
    "tables,rows,joins",
    [
        (
            ("t1", "t2", "t3"),
            (800, 400, 200),
            (
                JoinPredicate("t1", "k", "t2", "k"),
                JoinPredicate("t2", "k", "t3", "k"),
            ),
        ),
        (
            ("s1", "s2", "s3"),
            (50, 2000, 300),
            (
                JoinPredicate("s1", "id", "s2", "id"),
                JoinPredicate("s1", "id", "s3", "id"),
            ),
        ),
    ],
)
def test_unpublished_queries_match_spec_reference(planner, tables, rows, joins):
    query = Query(tables=tables, joins=joins)
    catalog = {
        name: TableStats(name, count, 1.0) for name, count in zip(tables, rows, strict=True)
    }
    got = planner.plan_query(query, catalog)
    expected = plan_query_reference(query, catalog)
    assert got.join_order == expected.join_order
    assert got.estimated_cost == pytest.approx(expected.estimated_cost)
    assert got.audit["plans_explored"] == expected.audit["plans_explored"]


def test_invalid_disconnected_graph_raises(planner):
    query = Query(
        tables=("left", "right", "lonely"),
        joins=(JoinPredicate("left", "a", "right", "a"),),
    )
    catalog = {
        "left": TableStats("left", 10, 1.0),
        "right": TableStats("right", 10, 1.0),
        "lonely": TableStats("lonely", 10, 1.0),
    }
    with pytest.raises(ValueError, match="no valid join order"):
        planner.plan_query(query, catalog)


def test_unpublished_sql_round_trip(planner):
    from optimizer.parser import parse_simple_sql

    sql = (
        "SELECT * FROM qp_alpha, qp_beta, qp_gamma "
        "WHERE qp_alpha.id = qp_beta.id AND qp_alpha.id = qp_gamma.id"
    )
    query = parse_simple_sql(sql)
    catalog = {
        "qp_alpha": TableStats("qp_alpha", 1800, 1.0),
        "qp_beta": TableStats("qp_beta", 90, 1.0),
        "qp_gamma": TableStats("qp_gamma", 360, 1.0),
    }
    got = planner.plan_query(query, catalog)
    expected = plan_query_reference(query, catalog)
    assert got.join_order == expected.join_order
    assert got.estimated_cost == pytest.approx(expected.estimated_cost)
