# Testing Strategy

This project maintains automated test suites to protect the integrity of the data compilation heuristics.

## Testing Philosophy
1. **Tests as Documentation**: Test cases describe exact parsing heuristics (e.g. how compensation amounts are parsed from sentences like "The landlord will pay the resident £150").
2. **Schema Verification**: Every database update must validate that the output SQLite files align strictly with target relational schemas.
3. **No Code Without Tests**: Any new parsing regex or database build logic must include corresponding tests.

## Test Directory Structure

All tests reside under `/tests/`:
- `test_extraction_functions.py`: Unit tests for text parsing (compensation, apologies).
- `test_section_splitter.py` / `test_section_helpers.py`: Tests for isolating complaint and finding sections.
- `test_schema.py`: Asserts table structure, primary keys, and constraint properties.
- `test_verify_insights.py`: Integration testing for canonical counts and upholding calculations.

## Running Tests

Ensure your virtual environment is configured with `uv`.

Run all tests:
```bash
uv run python -m pytest
```

Run tests matching a specific pattern:
```bash
uv run python -m pytest -k "compensation"
```

## Coverage Goals
- **Scraper and Compiler Heuristics**: 80% coverage minimum.
- **Extraction Logic**: 95% coverage minimum to guarantee regex changes do not break compensation or category classification rules.
