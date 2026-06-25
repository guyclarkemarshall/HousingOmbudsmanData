#!/bin/bash
# scripts/setup.sh — Run once when first cloning the repo
set -e
echo "=== Project Setup ==="

# Check prerequisites
command -v uv &>/dev/null || { echo "Install 'uv' first: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

# Install Python and sync dependencies
echo "Installing dependencies and python virtualenv via uv..."
uv sync

# Extract databases
echo "Extracting database archives..."
for f in ombudsman_decisions.zip ombudsman_insights.zip ombudsman_complaints_findings.zip; do
  if [ -f "$f" ]; then
    echo "Extracting $f..."
    unzip -o "$f"
  else
    echo "Warning: $f not found."
  fi
done

# Run tests
echo "Running verification tests..."
uv run python -m pytest

echo "=== Setup Complete ==="
echo "You can now run 'uv run verify-insights' or 'uv run verify-decisions' to check database stats."
