# Getting Started Guide

Welcome! This guide helps you get the UK Housing Ombudsman disputes dataset up and running on your local machine.

## Prerequisites

Before starting, ensure you have the following installed:
1. **Git**: Version control client.
2. **uv**: An extremely fast Python package and environment manager. Follow the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/).
3. **Python >= 3.11** (Usually handled automatically by `uv`).

---

## Setup Steps

### 1. Clone the Repository
```bash
git clone https://github.com/guyclarkemarshall/HousingOmbudsmanData.git
cd HousingOmbudsmanData
```

### 2. Run Setup Script

The setup script installs all project dependencies, creates a Python virtual environment, extracts the SQLite databases from their compressed archives, and runs verification checks.

- **On Windows (PowerShell)**:
  ```powershell
  PowerShell -ExecutionPolicy Bypass -File scripts/setup.ps1
  ```
- **On Unix (Mac/Linux)**:
  ```bash
  chmod +x scripts/setup.sh
  ./scripts/setup.sh
  ```

### 3. Verify Database Integrity

After the setup runs, verify the records loaded successfully:

```bash
# Verify the raw decisions database
uv run verify-decisions

# Verify the structured insights database
uv run verify-insights
```

These scripts print row counts, average compensation, and category metrics to confirm successful setup.

---

## Common Development Tasks

- **Running local tests**:
  ```bash
  uv run python -m pytest
  ```
- **Rebuilding Insights database**:
  ```bash
  uv run build-insights
  ```
- **Running the scraper**:
  ```bash
  # Scrape the first 5 index pages to update URLs
  uv run scrape --harvest --start-page 1 --end-page 5
  # Extract raw text from newly discovered URLs
  uv run scrape --extract
  ```
