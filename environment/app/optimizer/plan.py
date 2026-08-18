"""Query plan result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    join_order: tuple[str, ...]
    estimated_cost: float
    audit: dict
