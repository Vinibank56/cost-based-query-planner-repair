#!/usr/bin/env bash
# Reference implementation for cost-based-query-planner-repair.
set -euo pipefail

cp /solution/planner.py /app/optimizer/planner.py

python3 -m pytest \
  /tests/test_visible.py \
  /tests/test_hidden.py \
  /tests/test_behavior_hidden.py \
  /tests/test_statistical_hidden.py \
  /tests/test_edge_hidden.py \
  -q
