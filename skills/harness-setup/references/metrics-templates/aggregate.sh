#!/usr/bin/env bash
# Harness Metrics Aggregation Script
# 모든 aggregate-verdict.md (active + archive)를 순회하여 scorecard.md를 집계.
#
# 사용: bash .claude/runtime/harness-metrics/aggregate.sh
# 전제: python3 사용 가능

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export REPO_ROOT

python3 "$REPO_ROOT/.claude/runtime/harness-metrics/aggregate.py"
