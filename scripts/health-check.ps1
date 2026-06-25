# scripts/health-check.ps1 — Verifies project health on Windows
Write-Host "=== System Health Check ===" -ForegroundColor Green

$branch = git branch --show-current
Write-Host "Branch: $branch"

Write-Host "`n--- Verifying raw decisions database ---" -ForegroundColor Cyan
uv run python verify_db.py

Write-Host "`n--- Verifying insights database ---" -ForegroundColor Cyan
uv run python verify_insights.py

Write-Host "`n--- Running test suite ---" -ForegroundColor Cyan
uv run python -m pytest
