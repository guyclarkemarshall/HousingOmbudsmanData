#!/bin/bash
# scripts/start-dev.sh — Pre-flight developer check
echo "=== Pre-flight Checks ==="
echo "Branch: $(git branch --show-current)"
git status --short

echo "=== Local Database Status ==="
for f in ombudsman_decisions.db ombudsman_insights.db ombudsman_complaints_findings.db; do
  if [ -f "$f" ]; then
    echo "✓ $f ($(du -h "$f" | cut -f1))"
  else
    echo "✗ $f (Missing - run scripts/setup.sh)"
  fi
done

echo "=== Available CLI Commands ==="
echo "  uv run scrape             # Run the scraper"
echo "  uv run build-insights     # Regenerate insights DB"
echo "  uv run verify-insights    # Check insights database counts"
echo "  uv run verify-decisions   # Check raw decisions database counts"
echo "  uv run python -m pytest   # Run tests"
