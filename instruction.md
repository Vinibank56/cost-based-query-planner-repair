# Repair the cost-based query planner

You are taking over a simplified database engine at `/app`. The optimizer team needs a cost-based join planner for multi-table equi-join queries. DBAs audited the module and found systematic cost underestimation and suboptimal join orders that cause full-table scans on large intermediates.

Your job is to **fix only** `/app/optimizer/planner.py`. The companion modules (`catalog.py`, `cost.py`, `query.py`, `parser.py`, `plan.py`) are correct — do not modify them.

## Background

```
SQL string / Query object ──► plan_query() ──► Plan(join_order, estimated_cost, audit)
                                      ▲
                               TableStats catalog
```

The planner must:

1. **Enumerate** valid left-deep join orders (permutations where each new table connects to the already-joined subgraph).
2. **Estimate cost** using the provided scan and join cost helpers.
3. **Select** the minimum-cost plan and return a complete audit block.

The seed implementation passes smoke tests but fails production workloads. Your fix must satisfy the full contract below, including cases **not** listed in the self-check table.

## Cost model (canonical — use `cost.py`)

| Function | Formula |
|----------|---------|
| `scan_cost(stats)` | `stats.row_count * stats.scan_cost_per_row` |
| `join_cost(left_rows, right_rows, selectivity)` | `left_rows * right_rows * selectivity` |
| `output_rows(left_rows, right_rows, selectivity)` | `max(1, int(left_rows * right_rows * selectivity))` |
| `DEFAULT_SELECTIVITY` | `0.1` |

### Left-deep plan costing

For join order `(t0, t1, t2, ...)`:

1. Start with `rows = catalog[t0].row_count` and `total = scan_cost(catalog[t0])`.
2. For each subsequent table `ti`:
   - Add `scan_cost(catalog[ti])`.
   - Add `join_cost(rows, catalog[ti].row_count, DEFAULT_SELECTIVITY)`.
   - Update `rows = output_rows(rows, catalog[ti].row_count, DEFAULT_SELECTIVITY)`.

**Every table scan must be counted**, including the first table in the order.

## Requirements

Implement `plan_query` in `/app/optimizer/planner.py`:

```python
def plan_query(query: Query, catalog: dict[str, TableStats]) -> Plan:
```

### Validation

- Raise `ValueError("unknown table: {name}")` if any `query.tables` entry is missing from `catalog`.
- Raise `ValueError("no valid join order for query graph")` if no permutation satisfies connectivity (e.g., disconnected tables).

### Optimization

- Consider **all permutations** of `query.tables`.
- A permutation is valid when each table after the first is connected (via `query.joins` / `connected()`) to at least one table already in the joined set.
- Select the permutation with minimum total cost. On ties, keep the first minimum found (iteration order of `itertools.permutations`).

### Return shape (`Plan` dataclass)

| Field | Type | Meaning |
|-------|------|---------|
| `join_order` | `tuple[str, ...]` | Selected left-deep join order |
| `estimated_cost` | `float` | Total estimated cost |
| `audit` | `dict` | Diagnostics (see below) |

### Audit block

```python
{
    "plans_explored": int,      # count of valid permutations evaluated
    "selectivity": float,       # must be DEFAULT_SELECTIVITY (0.1)
    "algorithm": str,           # must be "left_deep_permutation"
}
```

## SQL parsing (provided — do not edit)

`parse_simple_sql(sql)` in `parser.py` parses queries of the form:

```sql
SELECT * FROM t1, t2, ... WHERE t1.a = t2.b AND ...
```

Your planner is called with the resulting `Query` object.

## Constraints

- Edit only `/app/optimizer/planner.py`.
- Use helpers in `cost.py`; do not hard-code cost formulas differently.
- Do not hard-code table names, join orders, or costs for specific queries.

## Success metrics

1. **Algorithmic** — valid permutation search with connectivity checking and minimum-cost selection.
2. **Visible suite** — `pytest /tests/test_visible.py` passes (self-check scenarios below).
3. **Hidden suite** — sealed tests verify chain/star graphs, unpublished catalog sizes, disconnected graphs, anti-greedy behavior, and equality against a hidden spec reference (you cannot inspect these tests).

> **Note:** Only `test_visible.py` scenarios are documented here. Hidden modules (`test_hidden.py`, `test_behavior_hidden.py`, `test_statistical_hidden.py`, `test_edge_hidden.py`) and `spec_reference.py` are sealed from the agent.

## Self-check examples (visible tests)

**Sample catalog:**

| Table | row_count | scan_cost_per_row |
|-------|-----------|-------------------|
| orders | 1000 | 1.0 |
| customers | 500 | 1.0 |
| products | 100 | 1.0 |

**Star query** — tables `orders`, `customers`, `products` with joins `orders.customer_id = customers.id` and `orders.product_id = products.id`:

| Check | Expected |
|-------|----------|
| `join_order` | `("orders", "products", "customers")` |
| `estimated_cost` | `511600.0` |
| `audit["plans_explored"]` | `4` |

**Two-table join** — `orders` ⋈ `customers` on `orders.customer_id = customers.id` with the sample catalog:

| Check | Expected |
|-------|----------|
| `estimated_cost` | `51500.0` |
| `audit["plans_explored"]` | `2` |

**SQL round-trip** — parse and plan:

```sql
SELECT * FROM orders, customers, products
WHERE orders.customer_id = customers.id AND orders.product_id = products.id
```

Expected `estimated_cost`: `511600.0`.

## Done when

`plan_query` satisfies the contract and passes visible, hidden, and behavioral verifier suites.
