"""Parsed query representation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JoinPredicate:
    left_table: str
    left_column: str
    right_table: str
    right_column: str


@dataclass(frozen=True)
class Query:
    """Simple multi-table equi-join query."""

    tables: tuple[str, ...]
    joins: tuple[JoinPredicate, ...]


def connected(a: str, b: str, joins: tuple[JoinPredicate, ...]) -> bool:
    """Return True if tables a and b share a join predicate."""
    for j in joins:
        pair = {j.left_table, j.right_table}
        if pair == {a, b}:
            return True
    return False
