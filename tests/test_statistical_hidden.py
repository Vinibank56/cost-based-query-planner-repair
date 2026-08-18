"""Hidden cost-model and optimization correctness tests."""

from __future__ import annotations

import pytest

from helpers import load_planner
from optimizer.catalog import TableStats
from optimizer.cost import DEFAULT_SELECTIVITY, join_cost, output_rows, scan_cost
from optimizer.query import JoinPredicate, Query
from spec_reference import plan_query_reference, recompute_left_deep_cost


@pytest.fixture(scope="module")
def planner():
    return load_planner()


def test_cost_includes_all_scan_and_join_terms(planner):
    query = Query(
        tables=("small", "large"),
        joins=(JoinPredicate("small", "k", "large", "k"),),
    )
    catalog = {
        "small": TableStats("small", 10, 2.0),
        "large": TableStats("large", 10000, 0.5),
    }
    plan = planner.plan_query(query, catalog)
    # Best order starts with small table
    assert plan.join_order[0] == "small"
    rows = 10
    expected = scan_cost(catalog["small"]) + scan_cost(catalog["large"]) + join_cost(
        rows, catalog["large"].row_count, DEFAULT_SELECTIVITY
    )
    assert plan.estimated_cost == pytest.approx(expected)


def test_reference_matrix_unseen_catalogs(planner):
    cases = [
        (
            Query(
                ("u1", "u2", "u3"),
                (
                    JoinPredicate("u1", "k", "u2", "k"),
                    JoinPredicate("u2", "k", "u3", "k"),
                ),
            ),
            {"u1": 900, "u2": 300, "u3": 50},
        ),
        (
            Query(
                ("hub", "a", "b"),
                (
                    JoinPredicate("hub", "id", "a", "id"),
                    JoinPredicate("hub", "id", "b", "id"),
                ),
            ),
            {"hub": 2000, "a": 100, "b": 400},
        ),
    ]
    for query, rows in cases:
        catalog = {n: TableStats(n, r, 1.0) for n, r in rows.items()}
        got = planner.plan_query(query, catalog)
        expected = plan_query_reference(query, catalog)
        assert got.join_order == expected.join_order
        assert got.estimated_cost == pytest.approx(expected.estimated_cost)
        assert got.audit == expected.audit


def test_row_estimates_use_product_selectivity(planner):
    """Join output cardinality must grow multiplicatively, not additively."""
    query = Query(
        tables=("p", "q"),
        joins=(JoinPredicate("p", "k", "q", "k"),),
    )
    catalog = {"p": TableStats("p", 100, 1.0), "q": TableStats("q", 100, 1.0)}
    plan = planner.plan_query(query, catalog)
    expected_rows_after = output_rows(100, 100, DEFAULT_SELECTIVITY)
    # Indirect check: cost uses product model; additive model would be cheaper
    additive_fake = scan_cost(catalog["p"]) + scan_cost(catalog["q"]) + (100 + 100)
    product_cost = scan_cost(catalog["p"]) + scan_cost(catalog["q"]) + join_cost(
        100, 100, DEFAULT_SELECTIVITY
    )
    assert plan.estimated_cost == pytest.approx(product_cost)
    assert plan.estimated_cost > additive_fake
    assert expected_rows_after == 1000


def test_three_table_cost_decomposition_uses_intermediate_cardinality(planner):
    """Downstream join cost must reflect product-based intermediate row counts."""
    query = Query(
        tables=("d", "e", "f"),
        joins=(
            JoinPredicate("d", "k", "e", "k"),
            JoinPredicate("e", "k", "f", "k"),
        ),
    )
    catalog = {
        "d": TableStats("d", 400, 1.0),
        "e": TableStats("e", 200, 1.0),
        "f": TableStats("f", 50, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    expected = plan_query_reference(query, catalog)
    assert plan.join_order == expected.join_order
    assert plan.estimated_cost == pytest.approx(expected.estimated_cost)


def test_scan_cost_per_row_influences_chain_plan(planner):
    """Scan weights interact with intermediate cardinalities on multi-join chains."""
    query = Query(
        tables=("x", "y", "z"),
        joins=(
            JoinPredicate("x", "k", "y", "k"),
            JoinPredicate("y", "k", "z", "k"),
        ),
    )
    catalog = {
        "x": TableStats("x", 5000, 1.0),
        "y": TableStats("y", 100, 25.0),
        "z": TableStats("z", 100, 1.0),
    }
    plan = planner.plan_query(query, catalog)
    expected = plan_query_reference(query, catalog)
    assert plan.join_order == expected.join_order
    assert plan.estimated_cost == pytest.approx(expected.estimated_cost)
    assert plan.estimated_cost < recompute_left_deep_cost(("x", "y", "z"), catalog)


@pytest.mark.parametrize(
    "tables,rows,joins",
    [
        (
            ("qp1", "qp2", "qp3"),
            (120, 600, 40),
            (
                JoinPredicate("qp1", "k", "qp2", "k"),
                JoinPredicate("qp1", "k", "qp3", "k"),
            ),
        ),
        (
            ("n1", "n2", "n3", "n4"),
            (300, 150, 75, 25),
            (
                JoinPredicate("n1", "k", "n2", "k"),
                JoinPredicate("n2", "k", "n3", "k"),
                JoinPredicate("n3", "k", "n4", "k"),
            ),
        ),
        (
            ("v1", "v2"),
            (2500, 120),
            (JoinPredicate("v1", "k", "v2", "k"),),
        ),
    ],
)
def test_unpublished_cost_matrix_matches_reference(planner, tables, rows, joins):
    query = Query(tables=tables, joins=joins)
    catalog = {
        name: TableStats(name, count, 1.0) for name, count in zip(tables, rows, strict=True)
    }
    got = planner.plan_query(query, catalog)
    expected = plan_query_reference(query, catalog)
    assert got.join_order == expected.join_order
    assert got.estimated_cost == pytest.approx(expected.estimated_cost)
    assert got.audit["plans_explored"] == expected.audit["plans_explored"]
