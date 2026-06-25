# Security & Data Protection Patterns

This document details the security and privacy guardrails implemented in this project to protect personal data and ensure system compliance with UK GDPR.

## Core Principles
1. **Rely Only on Publicly Redacted Data**: The scraper only downloads reports that have been publicly released and redacted by the UK Housing Ombudsman. 
2. **Prevent Re-Identification**: Never attempt to combine dataset records with outside datasets (e.g. electoral register, local news) to re-identify residents.
3. **No Private Personal Data Collection**: Avoid scraping names, phone numbers, email addresses, or specific flat numbers of tenants.

## Data Classification

| Category | Examples | Handling |
|----------|----------|---------|
| **Publicly Redacted Data** | Case text, decision dates, general landlord types | Normal database storage, commits are permitted |
| **Sensitive Corporate Data** | Internal API keys, scraper proxies | Stored in `.env` only (never committed to git) |
| **Personal Identifying Information (PII)** | Tenant names, specific addresses, medical details | **Prohibited**. Any accidental scrapings of this category must be immediately purged from the database and git history. |

## SQL Injection Prevention

When querying or building database records, always use parameterised queries via standard SQLite bindings:

```python
# ❌ WRONG
cursor.execute(f"SELECT * FROM cases WHERE case_id = '{case_id}'")

# ✅ RIGHT
cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
```

## Audit Logging

When running extraction or database builds, logs must never output tenant descriptors. Log execution milestones, row counts, and non-identifying codes:

```python
# ✅ RIGHT
logger.info(f"Processed case {case_id} successfully.")
```
