# ADR-001: SQLite Storage and Heuristic Compilation

**Status**: Accepted  
**Date**: 2026-06-25  
**Decision Makers**: Guy Clarke Marshall  
**Affected Components**: `scraper.py`, `build_insights_db.py`, `build_complaints_db.py`

## Context

The Housing Ombudsman portal contains tens of thousands of unstructured text decisions. To make this data useful for analytical querying, compliance mapping, and performance benchmarking, we need to extract structured fields (e.g. landlord name, total compensation ordered, specific complaint outcomes, cited legislation). 

Running LLM-based extraction on 16,600+ documents is cost-prohibitive (~$500 to $1,000 in API tokens) and difficult to replicate locally for open-source contributors. We need a performant, reproducible, and zero-cost strategy for compilation.

Additionally, the resulting dataset needs to be distributed in a format that:
1. Supports complex SQL querying.
2. Requires zero installation/setup of database servers (like PostgreSQL or MySQL).
3. Is lightweight enough to fit in GitHub repository file limits when compressed.

## Decision

We decided to:
1. Use **SQLite** as the primary storage format, packaged as compressed `.zip` archives.
2. Implement **regex-based text heuristics** and custom splitters (`section_splitter.py`) to parse unstructured documents into relational tables.
3. Validate heuristic compilation by comparing outputs against official Housing Ombudsman publications.

## Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **PostgreSQL Database** | Better concurrency, standard relational tooling | Requires hosting, setup, and credentials for contributors | Hard for non-technical users to set up locally |
| **Parquet / CSV files only** | Easy to open, good for Python/pandas | Lack of strict relational schemas, primary key constraints, and SQL support for non-programmers | Relational schema needs strict structure to preserve complaint-to-remedy mapping |
| **LLM-Based Parser (GPT-4/Claude)** | Better semantic understanding of fuzzy text | High API cost, slow, and non-deterministic results | Prohibitive cost and complexity for standard open-source contributors |

## Consequences

### Positive
- **Zero Cost**: Anyone can compile the dataset locally without API credentials.
- **Portability**: The SQLite databases (`ombudsman_decisions.db`, `ombudsman_insights.db`) can be shared easily, loaded in minutes, and queried using simple desktop tools (like DB Browser for SQLite).
- **High Speed**: The entire compilation heuristic suite compiles 16,611 cases in under a minute.

### Negative
- **Fuzzy Boundaries**: Regex heuristics can occasionally misclassify complex sentence structures, requiring periodic adjustments to splitters and extraction filters.

## Implementation Notes
Heuristic rules are covered by 166 pytest test cases under `/tests/` to guarantee that edits to regexes do not introduce regressions.
