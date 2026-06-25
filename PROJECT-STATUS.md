# Project Status
Last updated: 2026-06-25

## Current Phase: Active Development & Compilation

The project has compiled a robust dataset of housing dispute decisions from the UK Housing Ombudsman. It is currently in a state where the core crawling and text heuristics database compiler is working, verified, and produces three distinct databases.

## What's Working Now
- **Harvesting & Scraping**: Python crawling logic harvests dispute URLs from the public index and pulls decision texts. Over 16,611 records are captured.
- **Relational Insights Ingestion**: Rebuilding compiled insights standardizes landlord entities, aggregates total compensation, parses estimated compliance timescales, and registers legal citations.
- **Verification Suite**: Integrated verification tests check schema compliance, landlord records, and match outcomes against official 2024-25 severe maladministration publications with a 98.4% landlord name match rate.
- **Tests**: 166 passing unit and integration tests.

## What We're Building Next
- **Weekly Automated Synchronization**: Sync pipeline to check for new decisions on the Ombudsman portal.
- **Enhanced Categorization Models**: Implementing secondary heuristic and LLM evaluations to further refine dispute classification categories.
- **Additional Data Mapping**: Integration of National AddressBase Registry mapping (e.g. UPRN mapping verification).

## Active Work Streams

| Stream | Lead | Status | Good First Issues |
|--------|------|--------|-------------------|
| Scraper Optimization | @guyclarkemarshall | Running | Improve page-extraction regex |
| Validation Improvements | @guyclarkemarshall | Running | Add database record schema assertions |
| Sector Interoperability | @guyclarkemarshall | Planning | Standardize UPRN mapping |
