"""Shared helpers for query planner verifier tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def app_root() -> Path:
    if Path("/app").exists():
        return Path("/app")
    return Path(__file__).resolve().parents[1] / "environment" / "app"


def load_planner():
    root = str(app_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    for module_name in (
        "optimizer.planner",
        "optimizer.cost",
        "optimizer.query",
        "optimizer.catalog",
        "optimizer.parser",
        "optimizer.plan",
    ):
        if module_name in sys.modules:
            del sys.modules[module_name]
    return importlib.import_module("optimizer.planner")


def sample_catalog():
    from optimizer.catalog import sample_catalog as _sample

    return _sample()


def star_three_table_query():
    from optimizer.query import JoinPredicate, Query

    return Query(
        tables=("orders", "customers", "products"),
        joins=(
            JoinPredicate("orders", "customer_id", "customers", "id"),
            JoinPredicate("orders", "product_id", "products", "id"),
        ),
    )
