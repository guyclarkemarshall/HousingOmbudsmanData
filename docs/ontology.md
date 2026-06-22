# Housing Ombudsman Decisions — Domain Ontology

This document defines the entities, relationships, attributes, and hierarchies in the UK Housing Ombudsman decisions domain, derived from analysis of 16,611 decisions (2019–2026).

---

## Core Principles

1. **Case is the root entity.** Everything else relates back to a Case.
2. **Determinations are issue-level, not case-level.** A single case can have Maladministration on one issue and No Maladministration on another simultaneously.
3. **Complaint Handling is a process-layer category**, not a substantive one. It co-occurs with every substantive category (damp, ASB, repairs) — it is a meta-issue about how the landlord handled the complaint, layered on top of the underlying matter.
4. **Legal citations are case-level anchors**, not issue-specific — Housing Act 1996 and Housing Ombudsman Scheme appear in ~85–89% of all cases as jurisdictional boilerplate.

---

## Entity Hierarchy

```
Complaint (Case)
├── involves → Resident
├── against → Landlord
│   └── manages → Property
│       └── occupied under → Tenancy
├── contains → Issue (1..N)
│   ├── has → Determination (enum)
│   ├── classified as → Category (enum)
│   └── may cite → Legislation
├── investigated by → Ombudsman Investigation
│   └── produces → Decision
│       ├── contains → Order (0..N)
│       └── contains → Recommendation (0..N)
│           └── subtype → Compensation Award
└── has → Complaint Stage Response (1..N)
    └── may include → Compensation Offered
```

---

## Entities

### 1. Case (Complaint)

The central record. One formal complaint lodged with the Housing Ombudsman, after exhaustion of the landlord's internal process.

| Attribute | Type | Notes |
|---|---|---|
| `case_id` | string | Ombudsman reference number (e.g. `202347433`) |
| `title` | string | Landlord name + case_id |
| `decision_date` | date | Date of Ombudsman's published decision |
| `doc_format` | enum(`old`, `new`) | `old` = pre-Oct 2025 REPORT style; `new` = Nov 2025+ Investigation style |
| `is_upheld_est` | bool | True if any issue is upheld (Maladministration / Service Failure / Severe Maladministration) |
| `total_compensation_ordered` | float | Sum of all Compensation Orders |
| `stage_1_days_est` | int | Landlord's Stage 1 response time (days) |
| `stage_2_days_est` | int | Landlord's Stage 2 response time (days) |
| `timescales_exceeded_est` | bool | Whether landlord breached the Complaint Handling Code timescales |
| `apology_ordered_est` | bool | Ombudsman ordered written apology |
| `repairs_ordered_est` | bool | Ombudsman ordered physical works |
| `review_or_training_ordered_est` | bool | Ombudsman ordered policy review or staff training |
| `vulnerability_mentioned_est` | bool | Resident vulnerability factors noted |
| `communication_failure_est` | bool | Failure to communicate / update cited |
| `record_keeping_failure_est` | bool | Record-keeping failure cited |

**Relationships:**
- Case `involves` → 1 Resident
- Case `is against` → 1 Landlord
- Case `contains` → 1..N Issues
- Case `has` → 1..N Complaint Stage Responses
- Case `results in` → 1 Ombudsman Decision
- Case `cites` → 0..N Legislation

---

### 2. Issue (Finding)

A discrete complaint sub-part with its own individual determination. Most cases have 2–4 issues; distribution peaks at 2, with a long tail to 27.

| Attribute | Type | Notes |
|---|---|---|
| `description` | string | Sentence describing the issue and its outcome |
| `determination` | enum | See Determination taxonomy below |
| `category` | enum | See Category taxonomy below |
| `is_upheld_est` | bool | True if determination is Maladministration, Severe Maladministration, or Service Failure |

**Key insight:** A single Case can hold Issues with opposing determinations simultaneously (e.g. Maladministration on repairs + No Maladministration on ASB). Determinations are always per-Issue, never per-Case.

**Relationships:**
- Issue `belongs to` → 1 Case
- Issue `governed by` → 1 Determination (enum value)
- Issue `classified as` → 1 Category (enum value)

---

### 3. Determination (Enumeration)

Ordered severity scale — the Ombudsman's finding on a specific Issue.

| Value | Upheld? | Meaning |
|---|---|---|
| `Outside Jurisdiction` | No | Case/issue not within the Ombudsman's remit |
| `No Maladministration` | No | Landlord acted appropriately |
| `Reasonable Redress` | No (fault found, remedied) | Fault found but landlord already offered sufficient remedy before investigation concluded |
| `Service Failure` | **Yes** | Administrative or procedural failure causing some detriment |
| `Maladministration` | **Yes** | Significant failure in service, process, or policy application |
| `Severe Maladministration` | **Yes** | Serious / persistent failure with significant impact on the resident |

**Hierarchy:** Outside Jurisdiction < No Maladministration < Reasonable Redress < Service Failure < Maladministration < Severe Maladministration

---

### 4. Category (Enumeration — two-tier)

**Tier 1 — Substantive (the underlying issue):**

| Category | Covers |
|---|---|
| `Damp & Mould` | Condensation, rising damp, penetrating damp, mould growth |
| `Leaks & Water Ingress` | Burst pipes, roof leaks, flooding, drainage failures |
| `Repairs & Maintenance` | Boilers, windows, doors, roofs, lifts, gutters, structural works |
| `Pest Control` | Mice, rats, cockroaches, wasps, fleas, infestations |
| `Anti-Social Behaviour (ASB)` | Noise, harassment, nuisance, filming, verbal abuse |
| `Estate Management` | Communal areas, cleaning, refuse, bin stores, parking, gardens |
| `Rent & Service Charges` | Billing, arrears, service charge disputes |
| `Rehousing & Allocations` | Transfer requests, decants, homelessness, housing register |

**Tier 2 — Process (how the landlord managed the matter):**

| Category | Covers |
|---|---|
| `Complaint Handling` | Stage 1/2 timescales, response quality, escalation handling, KIM/record keeping during complaint |
| `Other` | Matters not fitting the above; catch-all |

**Key pattern:** Complaint Handling co-occurs with every substantive category (11,460 cases with Complaint Handling + Other; 4,936 with Complaint Handling + Damp & Mould). It should be understood as a process layer, not a peer category.

---

### 5. Landlord

The registered social landlord (RSL) or local authority against whom the complaint is made.

| Attribute | Type | Notes |
|---|---|---|
| `name` | string | Official registered name |
| `landlord_type` | enum | See below |

**Landlord Type Taxonomy:**
- `Housing Association` — registered providers (L&Q, Clarion, Peabody, Southern Housing, Stonewater, etc.)
- `Local Authority / ALMO or TMO` — council housing managed by arm's length body or tenant management organisation
- `Local Authority` — directly council-managed stock
- `For Profit` — private registered providers
- `Voluntary` — charitable/voluntary sector providers

**Note on data quality:** Landlord type is only populated for new-format (post-Nov 2025) documents (~1,917 cases). Legacy cases require external lookup.

**Relationships:**
- Landlord `owns or manages` → 1..N Properties
- Landlord `is subject of` → 1..N Cases
- Landlord `issues` → 1..N Complaint Stage Responses
- Landlord `deploys` → Contractors / Surveyors (per repair event)
- Landlord `governed by` → Policies (Repairs, Complaints, ASB, Compensation)

---

### 6. Resident

The complainant — the social housing tenant, leaseholder, or shared owner.

| Attribute | Type | Notes |
|---|---|---|
| `tenancy_type` | enum | See below |
| `is_vulnerable` | bool | Estimated from text |
| `vulnerability_details` | string | e.g. "kidney condition", "autistic child", "mental health" |

**Tenancy Type Taxonomy:**
- `Assured Tenancy` — standard private registered provider tenancy
- `Secure Tenancy` — council/local authority tenancy (stronger security of tenure)
- `Assured Shorthold Tenancy` — fixed-term, less security
- `Introductory Tenancy` — probationary council tenancy
- `Shared Ownership` — part-buy part-rent; hybrid obligations
- `Leaseholder` — long-lease owner in a block; distinct repair responsibilities
- `Applicant` — on housing register, not yet a tenant

**Relationships:**
- Resident `holds` → 1 Tenancy (which relates to 1 Property)
- Resident `raises` → 1..N Cases
- Resident `may be represented by` → Representative

---

### 7. Property

The dwelling at the centre of the complaint.

| Attribute | Type | Notes |
|---|---|---|
| `address` | string | — |
| `property_type` | string | Flat, house, studio, new build |
| `floor_level` | int | Relevant for damp, lift, access issues |
| `building_type` | string | Converted, purpose-built, high-rise |
| `freehold_structure` | string | Who owns the freehold (relevant for leaseholders) |

**Relationships:**
- Property `is occupied by` → Resident (under Tenancy)
- Property `is owned/managed by` → Landlord
- Property `is site of` → 1..N Repair/Defect events

---

### 8. Ombudsman Decision

The published formal outcome of the investigation.

| Attribute | Type | Notes |
|---|---|---|
| `decision_type` | enum(`Investigation`, `Report`) | `new` format = Investigation; `old` format = Report |
| `date` | date | Publication date |
| `total_orders` | int | Number of binding orders issued |
| `total_recommendations` | int | Number of non-binding recommendations |

**Relationships:**
- Decision `resolves` → 1 Case
- Decision `contains` → 0..N Orders
- Decision `contains` → 0..N Recommendations

---

### 9. Order

A binding directive from the Ombudsman requiring the landlord to act.

| Attribute | Type | Notes |
|---|---|---|
| `order_type` | enum | See below |
| `description` | string | Specific wording of the order |
| `due_date` | date | Compliance deadline |
| `amount` | float | If Compensation Order |

**Order Type Taxonomy:**
- `Compensation` — financial payment to resident
- `Apology` — written apology to resident
- `Repairs / Works` — complete specified physical works
- `Policy Review` — review and update landlord policy
- `Staff Training` — deliver training to relevant teams
- `Action Plan` — produce and share a documented remediation schedule
- `Meeting` — meet with resident to discuss outstanding matters
- `CCTV / Monitoring` — install evidence-gathering equipment (ASB cases)

**Distinction:** Orders are **binding**. Recommendations are **non-binding** — landlord may decline without consequence.

---

### 10. Complaint Stage Response

The landlord's formal response at each internal stage of the complaint process.

| Attribute | Type | Notes |
|---|---|---|
| `stage` | enum(`1`, `2`) | Stage 1 = first formal response; Stage 2 = final response before Ombudsman referral |
| `date_issued` | date | — |
| `response_days` | int | Days from complaint/escalation to response |
| `upheld` | bool | Whether landlord upheld the complaint at this stage |
| `compensation_offered` | float | Amount offered by landlord (not ordered by Ombudsman) |
| `standard_days` | int | Code target: Stage 1 = 10 working days; Stage 2 = 20 working days |
| `target_exceeded` | bool | Whether response_days > standard_days |

---

### 11. Legislation / Regulatory Framework

Statutes and codes cited within decisions.

| Statute | Relevance | Cases citing |
|---|---|---|
| Housing Ombudsman Scheme | Jurisdiction and powers | 14,716 (89%) |
| Housing Act 1996 | Primary legislation | 14,091 (85%) |
| Landlord and Tenant Act 1985 | Repair obligations (s.11) | 2,403 (14%) |
| Housing Health and Safety Rating System (HHSRS) | Hazard assessment | 2,840 (17%, incl. duplicates) |
| Equality Act 2010 | Disability / vulnerability obligations | 632 (4%) |
| Decent Homes Standard | Physical condition standard | 402 (2%) |
| Homes (Fitness for Human Habitation) Act 2018 | Fitness standard | 220 (1%) |
| Awaab's Law | Damp/mould response timescales | small (emerging) |
| Human Rights Act | Article 8 (private life/home) | 72 |
| Care Act 2014 | Vulnerability / social care | 17 |

---

## Relationship Map (Complete)

```
Resident ─── holds ──────────────────────────────► Tenancy
                                                        │
                                                   relates_to
                                                        ▼
Landlord ─── owns/manages ──────────────────────► Property
    │
    │ is_governed_by
    ▼
  Policy
  (Repairs / Complaints / ASB / Compensation)

Resident ─── raises ────────────────────────────► Case
                                                    │
Case ─── is_against ────────────────────────────► Landlord
Case ─── contains ──────────────────────────────► Issue (1..N)
                                                    │
                                                    ├─ has_determination ─► Determination (enum)
                                                    └─ classified_as ─────► Category (enum)

Case ─── has_stage_response ────────────────────► Complaint Stage Response (1..N)
                                                    │
                                          offers_compensation
                                                    ▼
                                           Compensation Offered
                                           (by Landlord, pre-decision)

Case ─── investigated_by ───────────────────────► Ombudsman Investigation
                                                    │
                                              produces
                                                    ▼
                                           Ombudsman Decision
                                                    │
                                        ┌───────────┴───────────┐
                                   contains                  contains
                                        ▼                        ▼
                                     Order (0..N)        Recommendation (0..N)
                                        │
                              ┌─────────┴──────────────┐
                         Compensation              Apology / Works /
                           Award                  Policy Review / Training

Case ─── cites ─────────────────────────────────► Legislation (0..N)
```

---

## Process Flow (Temporal)

```
1. INCIDENT
   Resident reports defect/ASB to Landlord
   (may repeat over months/years; each report is date-stamped)

2. LANDLORD ACTION
   Contractor visits, surveys, access attempts, works scheduled
   ("calling cards" left when no access)

3. COMPLAINT RAISED (Stage 1)
   Landlord must: acknowledge ≤ 5 working days
                  respond     ≤ 10 working days

4. STAGE 1 RESPONSE
   Landlord: upholds / partially upholds / rejects
   May offer compensation; resident may accept or escalate

5. ESCALATION (Stage 2)
   Landlord must: acknowledge ≤ 5 working days
                  respond     ≤ 20 working days

6. STAGE 2 FINAL RESPONSE
   Landlord's final internal position

7. REFERRAL TO OMBUDSMAN
   Resident refers case; Ombudsman assesses jurisdiction

8. INVESTIGATION
   Evidence reviewed from both parties
   Landlord may make further offers during this phase

9. DECISION PUBLISHED
   Findings per Issue; Orders and Recommendations issued with due dates

10. COMPLIANCE
    Landlord evidences compliance per Order due dates
```

---

## Key Ontological Patterns

### Pattern 1: Process Failure is Orthogonal to Substantive Failure
A case about damp will almost always also have a Complaint Handling issue. These are independent axes:
- **Substantive axis**: What went wrong with the property/service?
- **Process axis**: How well did the landlord handle the complaint about it?

### Pattern 2: Severity × Persistence × Impact
The three dimensions that distinguish Maladministration from Severe Maladministration:
- **Severity** of the failure itself
- **Persistence** (was it an isolated incident or repeated over time?)
- **Impact** on the resident (especially where vulnerable)

Compensation awards reflect all three: Rehousing failures (£6,033 avg for Severe Maladministration) command far higher awards than Complaint Handling failures (£1,204 avg), reflecting the gravity of denying housing access.

### Pattern 3: Landlord Type Moderates Outcomes
Housing Associations account for ~82% of cases with landlord_type populated. Local Authorities have a higher proportion of No Maladministration findings, possibly reflecting different regulatory context and legal frameworks (secure tenancy vs. assured tenancy).

### Pattern 4: Vulnerability Amplifies Awards
Vulnerability (mentioned in 74% of cases) is a consistent amplifier — cases involving vulnerable residents with unresolved damp, or ASB affecting children, typically receive higher severity determinations and larger compensation orders.

### Pattern 5: Legal Citations as Jurisdictional Anchors vs Substantive Arguments
- Housing Ombudsman Scheme + Housing Act 1996 = jurisdictional boilerplate (cited in ~85–89% of all cases)
- Landlord and Tenant Act 1985 + HHSRS = substantive anchor for repair/condition cases (14–17%)
- Equality Act 2010 = vulnerability/disability context (4%)
- Awaab's Law / Homes (Fitness for Human Habitation) Act = emerging; will grow in new-format docs

---

## Ontology Summary Diagram

```
                    ┌─────────────────────┐
                    │      LEGISLATION     │
                    │  Housing Act 1996   │
                    │  HOS Scheme         │
                    │  LTA 1985, HHSRS    │
                    └──────────┬──────────┘
                               │ cited_in
                               ▼
┌──────────┐    raises    ┌───────────────────────────────────────────────┐
│ RESIDENT │────────────►│                    CASE                        │
│          │             │  case_id · decision_date · doc_format           │
│ tenancy  │             │  is_upheld · total_comp · vulnerability         │
│ type     │             │  timescales · remedies ordered                  │
│ vuln?    │             └────────────────┬──────────────────────────────┘
└──────────┘                              │
                                   ┌──────┴───────┐
                              is_against        contains (1..N)
                                   │                  │
                                   ▼                  ▼
                          ┌──────────────┐    ┌────────────────────┐
                          │   LANDLORD   │    │       ISSUE         │
                          │              │    │                     │
                          │ name         │    │ description         │
                          │ landlord_type│    │ determination ◄─────┼── DETERMINATION
                          └──────────────┘    │ category ◄──────────┼── CATEGORY
                                              │ is_upheld           │   (2-tier)
                                              └────────────────────┘

                          ┌───────────────────────────────┐
                          │       OMBUDSMAN DECISION       │
                          │                               │
                          │  ┌─────────┐  ┌────────────┐ │
                          │  │  ORDER  │  │   RECOM-   │ │
                          │  │         │  │ MENDATION  │ │
                          │  │ type    │  │            │ │
                          │  │ amount? │  │ (non-bind) │ │
                          │  │ due_date│  └────────────┘ │
                          │  └─────────┘                 │
                          └───────────────────────────────┘
```
