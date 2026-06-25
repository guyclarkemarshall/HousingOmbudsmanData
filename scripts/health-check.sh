#!/bin/bash
# scripts/health-check.sh — Verifies project health
echo "=== System Health Check ==="
echo "Branch: $(git branch --show-current)"

echo "--- Verifying raw decisions database ---"
uv run python verify_db.py

echo "--- Verifying insights database ---"
uv run python verify_insights.py

echo "--- Running test suite ---"
uv run python -m pytest
