# Data Standards

To guarantee high analysis accuracy and system interoperability within the UK Housing Sector, we define specific data representation standards.

## Landlord Standardisation

Landlords are identified by standard cased names matching the canonical labels used in official Housing Ombudsman reviews (e.g. `Peabody Trust`, `Lambeth Council`).
- Scraped preambles may contain variations (e.g., `Lambeth LBC`, `London Borough of Lambeth`).
- During compilation, names are canonicalized to a unified representation. The script `verify_against_official.py` checks these matches.

## UPRN (Unique Property Reference Number)

The UPRN is the standard identifier for properties in the UK.
- **Goal**: When property address details are available in the public preambles, they should map to UPRN tags.
- **Graceful degradation**: As address preambles are frequently redacted or incomplete, the schema supports optional UPRN fields.

## Dispute Categories

All issue findings are classified into one of the following canonical categories:
1. **Damp & Mould**
2. **Leaks & Water Ingress**
3. **Repairs & Maintenance**
4. **Pest Control**
5. **Complaint Handling**
6. **Anti-Social Behaviour (ASB)**
7. **Estate Management**
8. **Rent & Service Charges**
9. **Rehousing & Allocations**
10. **Other**

## Determination Categories

Determinations must map to official outcomes:
- **Severe Maladministration** (Upheld)
- **Maladministration** (Upheld)
- **Service Failure** (Upheld)
- **Reasonable Redress** (Not Upheld)
- **No Maladministration** (Not Upheld)
- **Outside Jurisdiction** (Excluded)
