"""Cost model helpers for join planning."""

from __future__ import annotations

from optimizer.catalog import TableStats

DEFAULT_SELECTIVITY = 0.1


def scan_cost(stats: TableStats) -> float:
    """Cost to read a base table."""
    return stats.row_count * stats.scan_cost_per_row


def join_cost(left_rows: int, right_rows: int, selectivity: float = DEFAULT_SELECTIVITY) -> float:
    """Cost of a binary equi-join given cardinalities."""
    return left_rows * right_rows * selectivity


def output_rows(left_rows: int, right_rows: int, selectivity: float = DEFAULT_SELECTIVITY) -> int:
    """Estimated rows produced by a join."""
    return max(1, int(left_rows * right_rows * selectivity))
