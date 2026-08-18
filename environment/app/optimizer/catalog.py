"""Catalog statistics for cost estimation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableStats:
    name: str
    row_count: int
    scan_cost_per_row: float


def sample_catalog() -> dict[str, TableStats]:
    """Default catalog used in visible verifier fixtures."""
    return {
        "orders": TableStats("orders", 1000, 1.0),
        "customers": TableStats("customers", 500, 1.0),
        "products": TableStats("products", 100, 1.0),
    }
