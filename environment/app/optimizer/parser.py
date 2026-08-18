"""SQL parser for a restricted join subset."""

from __future__ import annotations

import re

from optimizer.query import JoinPredicate, Query

_FROM_RE = re.compile(
    r"FROM\s+(.+?)\s+WHERE\s+(.+)",
    re.IGNORECASE | re.DOTALL,
)
_JOIN_RE = re.compile(
    r"(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)",
    re.IGNORECASE,
)


def parse_simple_sql(sql: str) -> Query:
    """
    Parse queries of the form:
    SELECT * FROM t1, t2, ... WHERE t1.a = t2.b AND ...
    """
    match = _FROM_RE.search(sql.strip())
    if not match:
        raise ValueError("unsupported SQL shape")

    tables_raw, where_raw = match.groups()
    tables = tuple(t.strip() for t in tables_raw.split(","))
    if len(set(tables)) != len(tables):
        raise ValueError("duplicate table in FROM clause")

    joins: list[JoinPredicate] = []
    for pred in where_raw.split("AND"):
        pred = pred.strip()
        jmatch = _JOIN_RE.fullmatch(pred)
        if not jmatch:
            raise ValueError(f"unsupported predicate: {pred}")
        lt, lc, rt, rc = jmatch.groups()
        if lt not in tables or rt not in tables:
            raise ValueError("join references unknown table")
        joins.append(JoinPredicate(lt, lc, rt, rc))

    return Query(tables=tables, joins=tuple(joins))
