# scripts/start-dev.ps1 — Pre-flight developer check
Write-Host "=== Pre-flight Checks ===" -ForegroundColor Green

$branch = git branch --show-current
Write-Host "Branch: $branch"

git status --short

Write-Host "`n=== Local Database Status ===" -ForegroundColor Green
$dbs = @("ombudsman_decisions.db", "ombudsman_insights.db", "ombudsman_complaints_findings.db")
foreach ($db in $dbs) {
    if (Test-Path $db) {
        $size = (Get-Item $db).Length
        $size_str = "{0:N2} MB" -f ($size / 1MB)
        Write-Host "✓ $db ($size_str)" -ForegroundColor Green
    } else {
        Write-Host "✗ $db (Missing - run scripts/setup.ps1)" -ForegroundColor Red
    }
}

Write-Host "`n=== Available CLI Commands ===" -ForegroundColor Cyan
Write-Host "  uv run scrape             # Run the scraper"
Write-Host "  uv run build-insights     # Regenerate insights DB"
Write-Host "  uv run verify-insights    # Check insights database counts"
Write-Host "  uv run verify-decisions   # Check raw decisions database counts"
Write-Host "  uv run python -m pytest   # Run tests"
