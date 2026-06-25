# CLAUDE.md — Agent Constitution for OmbudsmanScraper

This document outlines coding rules, architecture boundaries, domain requirements, and testing conventions for the Housing Ombudsman Disputes Dataset project.

---

## Domain Context (UK Social Housing)

This repository hosts a public dataset of UK Housing Ombudsman disputes. Treat all data with domain-informed care:
- **No re-identification**: Do not collect, enrich, or output individual tenant names, exact addresses, or tenant contact details. All data must remain strictly anonymized.
- **Accuracy matters**: Decisions are used by landlords for policy benchmarks and by legal advocates. Extracted compensation, categories, and determinations must be highly accurate.
- **Awaab's Law Compliance**: Keep special tracking of "Damp & Mould" and corresponding landlord response timescales.

---

## Development Constraints & Rules

### Data & SQL Integrity — CRITICAL
- **Parameterised Queries**: Always use placeholder bindings in database queries. Never build SQL queries using string formatting.
- **Anonymization Check**: Never write prints, logs, or comments referencing private tenant information.

### Layer Boundaries

| Component | Responsibility | Allowed Imports |
|-----------|----------------|-----------------|
| **Scraper** (`scraper.py`) | Harvesting index pages, raw page download, DB storage | `urllib`, `requests`, `bs4`, `sqlite3` |
| **Section Splitter** (`section_splitter.py`) | Isolating complaint sections, parsing preambles | `re` |
| **Compiler** (`build_insights_db.py`) | Compiling relational structures, standardizing landlords | `sqlite3`, `re`, `section_splitter` |
| **Verification** (`verify_against_official.py`) | Auditing data representation against official summaries | `sqlite3`, `json` |

---

## Edge Case Awareness

- **Landlord Standardisation**: Landlords can appear under various names (e.g. `Peabody`, `Peabody Trust`). Always map variations to canonical names.
- **Compensation Aggregation**: Aggregate multiple small ordered amounts correctly to calculate `total_compensation_ordered`.
- **Preambles Format**: Pre-Oct 2025 reports have different layouts from Nov 2025+ investigations. Check `doc_format` (`old` vs `new`) before using split heuristics.

---

## Testing Protocol

Ensure all tests pass before proposing updates:
- Run test suite: `uv run python -m pytest`
- Check specific file: `uv run python -m pytest tests/test_schema.py`
- Test coverage must be preserved at a minimum of 80% for all compilation logic.
