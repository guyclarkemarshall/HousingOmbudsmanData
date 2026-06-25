# scripts/setup.ps1 — Windows PowerShell Setup Script
$ErrorActionPreference = "Stop"

Write-Host "=== Project Setup ===" -ForegroundColor Green

# Check for uv
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Error "Install 'uv' first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

# Install dependencies
Write-Host "Installing dependencies and python virtualenv via uv..." -ForegroundColor Cyan
uv sync

# Extract databases
Write-Host "Extracting database archives..." -ForegroundColor Cyan
$zips = @("ombudsman_decisions.zip", "ombudsman_insights.zip", "ombudsman_complaints_findings.zip")
foreach ($zip in $zips) {
    if (Test-Path $zip) {
        Write-Host "Extracting $zip..."
        Expand-Archive -Force -Path $zip -DestinationPath .
    } else {
        Write-Host "Warning: $zip not found." -ForegroundColor Yellow
    }
}

# Run tests
Write-Host "Running verification tests..." -ForegroundColor Cyan
uv run python -m pytest

Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "You can now run 'uv run verify-insights' or 'uv run verify-decisions' to check database stats." -ForegroundColor Green
