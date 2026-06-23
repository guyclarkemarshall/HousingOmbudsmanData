# Housing Ombudsman Decisions — Domain Ontology

Defines the entities, predicates, taxonomies, and temporal flow of the UK Housing Ombudsman decisions domain.

---

## Core Principles

1. **Case is the root entity.** All other entities relate back to a Case.
2. **Determinations are issue-level, not case-level.** A single case can carry Maladministration on one issue and No Maladministration on another simultaneously.
3. **Complaint Handling is a process-layer category.** It describes how the landlord handled the complaint — a meta-issue that co-occurs with every substantive category. It is not a peer of Damp & Mould or ASB.
4. **Orders are binding; Recommendations are not.** A landlord must comply with Orders within the stated deadline and evidence that compliance. Recommendations may be declined without consequence.
5. **Compensation is issue-level.** A compensation award relates to the specific Issue that caused the resident harm, not to the Case in aggregate.
6. **Outside Jurisdiction is an intake-level decision, not an issue-level determination.** If the Ombudsman determines a case falls outside its remit, no Investigation occurs and no Issue-level findings are made.
7. **Reasonable Redress is a resolution pathway, not a severity level.** It means a proportionate remedy has been offered; the underlying failure could have been Maladministration or Severe Maladministration had it not been remedied.

---

## Entity Hierarchy

```
Case
├── involves ──────────────► Resident
│                               └── holds ──► Tenancy (1..N, current flagged)
│                                               └── relates_to ──► Property
├── is_against ─────────────► Landlord
│                               ├── owns_or_manages ──► Property
│                               └── managed_by ────────► ManagementStructure (ALMO/TMO)
├── contains ───────────────► Issue (1..N)
│                               ├── has_determination ──► Determination (enum)
│                               └── classified_as ──────► Category (enum)
├── has_stage_response ─────► ComplaintStageResponse (Stage 1: 1, Stage 2: 0..1)
│                               └── offered_compensation_of ──► float
├── results_in ─────────────► OmbudsmanDecision (0..1)
│                               ├── contains_order ──────► Order (0..N)
│                               │                            └── compensates_for ──► Issue (if Compensation type)
│                               └── contains_recommendation ► Recommendation (0..N)
├── has_compliance_record ──► ComplianceRecord (per Order)
└── cites ──────────────────► Legislation (0..N)
```

---

## Entities

### Case

The central record. One formal complaint lodged with the Housing Ombudsman after exhaustion of the landlord's internal complaint process. A Case without an OmbudsmanDecision exists where the case is withdrawn, referred back, resolved early, or is still under investigation.

| Attribute | Type | Description |
|---|---|---|
| `case_id` | string | Ombudsman reference number (e.g. `202347433`) |
| `title` | string | Full case title as published |
| `decision_date` | date | Date of Ombudsman's published decision (null if no decision yet) |
| `doc_format` | enum(`old`, `new`) | Document structure: `old` = REPORT style; `new` = Investigation style with repeating Complaint/Finding sections. Transition occurred gradually across 2024–2025. |
| `intake_outcome` | enum(`accepted`, `outside_jurisdiction`, `referred_back`, `early_resolution`, `withdrawn`) | Result of the Ombudsman's intake/jurisdiction assessment, before any formal investigation |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `involves` | Case → | Resident | 1..N (1 for sole tenant; 2 for joint tenants) |
| `is_against` | Case → | Landlord | 1 |
| `concerns_property` | Case → | Property | 0..1 |
| `contains` | Case → | Issue | 1..N (only if intake_outcome = `accepted`) |
| `has_stage_response` | Case → | ComplaintStageResponse | 1..2 (Stage 1 always; Stage 2 where escalated) |
| `results_in` | Case → | OmbudsmanDecision | 0..1 |
| `has_compliance_record` | Case → | ComplianceRecord | 0..N (one per Order) |
| `cites` | Case → | Legislation | 0..N |
| `related_to` | Case → | Case | 0..N (same property, same resident, follow-on) |

---

### Issue

A discrete complaint sub-part within an accepted case. Each issue receives its own individual determination. A case typically contains 2–4 issues.

| Attribute | Type | Description |
|---|---|---|
| `description` | string | The specific complaint sub-matter (e.g. "handling of damp report") |
| `determination` | Determination | The Ombudsman's ruling on this issue |
| `category` | Category | Classified dispute type |
| `is_upheld` | bool | True if determination is Maladministration, Severe Maladministration, or Service Failure |
| `sequence_number` | int | Ordering of this issue within the case (substantive issues typically precede complaint handling issues) |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `part_of` | Issue → | Case | 1 |
| `has_determination` | Issue → | Determination | 1 |
| `classified_as` | Issue → | Category | 1 |
| `compensated_by` | Issue ← | Order (Compensation type) | 0..N |
| `governed_by` | Issue → | Legislation | 0..N |

---

### Determination

The Ombudsman's formal ruling on a specific Issue (for accepted, investigated cases only).

**Findings (severity-ordered):**

| Value | Upheld? | Meaning |
|---|---|---|
| `No Maladministration` | No | Landlord acted appropriately |
| `Service Failure` | **Yes** | Administrative or procedural failure causing some detriment |
| `Maladministration` | **Yes** | Significant failure in service, process, or policy application |
| `Severe Maladministration` | **Yes** | Serious or persistent failure with significant impact on the resident |

**Severity order:** No Maladministration < Service Failure < Maladministration < Severe Maladministration

**Resolution pathway (separate from the severity scale):**

| Value | Meaning |
|---|---|
| `Reasonable Redress` | A proportionate remedy has been offered by the landlord and accepted (or would be reasonable to accept). The underlying conduct may have warranted Maladministration or Severe Maladministration had the remedy not been made. This is a resolution outcome, not a severity finding. |

**Note on Outside Jurisdiction:** This is an intake-level decision recorded on `Case.intake_outcome`, not an issue-level determination. If a case is outside jurisdiction, no Issues are created and no investigation takes place.

---

### Category

The type of complaint. Two-tier model: substantive (what the dispute is about) and process (how the landlord handled it).

**Tier 1 — Substantive:**

| Category | Covers |
|---|---|
| `Damp & Mould` | Condensation, rising damp, penetrating damp, mould growth |
| `Leaks & Water Ingress` | Burst pipes, roof leaks, flooding, drainage failures |
| `Repairs & Maintenance` | Responsive repairs — boilers, windows, doors, roofs, lifts, gutters, structural defects |
| `Planned & Major Works` | Cyclical decoration, kitchen/bathroom programmes, planned maintenance schemes |
| `Pest Control` | Mice, rats, cockroaches, wasps, fleas, infestations |
| `Anti-Social Behaviour (ASB)` | Noise (behavioural), harassment, nuisance, filming, verbal abuse |
| `Estate Management` | Communal areas, cleaning, refuse, bin stores, parking, gardens |
| `Rent & Service Charges` | Billing, arrears, service charge disputes |
| `Leasehold & Service Charges` | Section 20 consultation, service charge reasonableness, leaseholder-specific obligations |
| `Rehousing & Allocations` | Transfer requests, decants, homelessness, housing register |
| `Mutual Exchange` | Mutual exchange requests under the Localism Act 2011 |
| `Right to Buy / Right to Acquire` | Statutory purchase rights, valuations, delays |
| `Building Safety` | EWS1 forms, cladding remediation, waking watch, flat sales blocked by building safety works |
| `Fire Safety` | Fire door maintenance, fire risk assessments, communal fire detection systems |
| `Domestic Abuse` | Re-housing requests, data protection, mutual exchange, and case handling for DA cases |

**Tier 2 — Process:**

| Category | Covers |
|---|---|
| `Complaint Handling` | Stage 1/2 timescales, acknowledgement failures, response quality, escalation handling, record keeping during the complaint |
| `Other` | Matters not fitting the above |

**Key pattern:** Complaint Handling co-occurs with every substantive category. A damp case will almost always also carry a Complaint Handling issue — these are independent axes, not alternatives.

---

### Landlord

The registered social landlord (RSL) or local authority that is the respondent in the case. Where an ALMO or TMO manages stock on behalf of a local authority, the stock-owning authority is the Landlord; the management organisation is a separate `ManagementStructure` entity.

| Attribute | Type | Description |
|---|---|---|
| `name` | string | Official registered name |
| `landlord_type` | LandlordType | Classification of the stock-owning organisation |
| `management_structure` | enum(`direct`, `ALMO`, `TMO`, `contracted_out`, `none`) | How day-to-day housing management is delivered |

**LandlordType taxonomy:**

| Value | Description |
|---|---|
| `Housing Association` | Registered providers (L&Q, Clarion, Peabody, Southern Housing, Stonewater, etc.) |
| `Local Authority` | Council directly managing its own stock |
| `For Profit` | Private equity-backed or commercially structured registered providers |
| `Voluntary` | Charitable or voluntary sector providers |

**Note on ALMOs and TMOs:** An ALMO (Arms Length Management Organisation) or TMO (Tenant Management Organisation) manages stock owned by a local authority but is not itself the landlord for Ombudsman purposes. Complaints are made against the stock-owning local authority. Use `management_structure = ALMO` or `TMO` on the `Landlord` entity to capture this.

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `owns_or_manages` | Landlord → | Property | 1..N |
| `is_subject_of` | Landlord ← | Case | 1..N |
| `issues_response_in` | Landlord → | ComplaintStageResponse | 1..N |

---

### Resident

The complainant — a social housing tenant, leaseholder, or shared owner. Pre-tenancy applicants raising allocation complaints are also Residents in this model, with a null Tenancy.

| Attribute | Type | Description |
|---|---|---|
| `resident_status` | enum(`applicant`, `current_tenant`, `former_tenant`, `leaseholder`, `shared_owner`) | Legal status at time of complaint |
| `is_vulnerable` | bool | Vulnerability factors noted (health, disability, mental health, age, children) |
| `vulnerability_details` | string | Free text (e.g. "kidney condition", "autistic child", "mental health diagnosis") |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `holds` | Resident → | Tenancy | 0..N (0 for applicants; 1..N over time, with is_current flag) |
| `raises` | Resident → | Case | 1..N |

---

### Tenancy

The legal relationship between one or more Residents and a Landlord over a specific Property. Joint tenancies have multiple Residents.

| Attribute | Type | Description |
|---|---|---|
| `tenancy_type` | TenancyType | Classification of tenure |
| `is_current` | bool | True if this is the active tenancy at time of complaint |
| `start_date` | date | Tenancy commencement date |

**TenancyType taxonomy:**

| Value | Description |
|---|---|
| `Assured Tenancy` | Standard private registered provider tenancy; primary tenure for housing association residents |
| `Secure Tenancy` | Council / local authority tenancy; stronger security of tenure than Assured |
| `Introductory Tenancy` | Probationary council tenancy (12-month trial period before conversion to Secure) |
| `Starter Tenancy` | Housing association equivalent of Introductory — an AST used as a probationary mechanism before conversion to Assured |
| `Shared Ownership` | Part-buy part-rent; hybrid repair and service charge obligations |
| `Leaseholder` | Long-lease owner in a block; repair responsibilities differ from landlord's obligations to tenants |
| `Demoted Tenancy` | A downgraded form of Secure or Assured tenancy imposed as an ASB management tool; reduced security of tenure |
| `Assured Shorthold Tenancy` | Fixed-term, limited security; rare in this dataset (applies mainly to HA temporary accommodation) |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `held_by` | Tenancy → | Resident | 1..N (1 for sole tenant; 2+ for joint tenants) |
| `relates_to` | Tenancy → | Property | 1 |
| `granted_by` | Tenancy → | Landlord | 1 |

---

### Property

The dwelling at the centre of the complaint.

| Attribute | Type | Description |
|---|---|---|
| `address` | string | Street address |
| `property_type` | string | Flat, house, studio, new build |
| `floor_level` | int | Relevant for damp, lift access, and flooding issues |
| `building_type` | string | Converted, purpose-built, high-rise |
| `freehold_structure` | string | Who holds the freehold (material for leasehold cases) |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `owned_or_managed_by` | Property → | Landlord | 1 |

---

### OmbudsmanDecision

The published formal outcome of the Ombudsman's investigation. Exists only for cases where `intake_outcome = accepted` and the investigation has concluded. A Case with no OmbudsmanDecision is under investigation, resolved early, withdrawn, or outside jurisdiction.

| Attribute | Type | Description |
|---|---|---|
| `decision_type` | enum(`Investigation`, `Report`) | `Investigation` = new document style; `Report` = legacy document style |
| `date` | date | Publication date |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `resolves` | OmbudsmanDecision → | Case | 1 |
| `contains_order` | OmbudsmanDecision → | Order | 0..N |
| `contains_recommendation` | OmbudsmanDecision → | Recommendation | 0..N |

---

### Order

A binding directive from the Ombudsman requiring the landlord to act within a stated deadline. Non-compliance can be escalated to the Regulator of Social Housing or pursued under the Ombudsman's enforcement powers (Social Housing (Regulation) Act 2023).

| Attribute | Type | Description |
|---|---|---|
| `order_type` | OrderType | Classification of the remedy |
| `description` | string | Specific wording of the order |
| `due_date` | date | Compliance deadline |
| `amount` | float | Monetary value (populated only when order_type is `Compensation`) |

**OrderType taxonomy:**

| Value | Description |
|---|---|
| `Compensation` | Financial payment to the resident |
| `Apology` | Written apology to the resident |
| `Repairs / Works` | Complete specified physical works at the property |
| `Reinspection / Survey` | Commission a specific survey (damp survey, structural survey, HHSRS inspection) |
| `Policy Review` | Review and update landlord policy or procedure |
| `Record-Keeping Review` | Specifically address document and data management failures |
| `Staff Training` | Deliver training to relevant teams |
| `Action Plan` | Produce and share a documented remediation schedule |
| `Meeting` | Meet with resident to discuss outstanding matters |
| `CCTV / Monitoring` | Install evidence-gathering equipment (ASB cases) |
| `Decant / Suitable Alternative Accommodation` | Direct landlord to decant resident where property is uninhabitable (Severe Maladministration cases) |
| `Complaint Handling Failure Order (CHFO)` | Issued where a landlord fails to engage with the complaints process; distinct from a post-determination Order; introduced under the Social Housing (Regulation) Act 2023 |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `contained_in` | Order → | OmbudsmanDecision | 1 |
| `compensates_for` | Order (Compensation type) → | Issue | 1 |

**Note:** `compensates_for` applies only to Orders of type `Compensation`. It is the most analytically important predicate — it links a financial award to the specific Issue that caused the harm, enabling per-issue compensation analysis.

---

### Recommendation

A non-binding suggestion from the Ombudsman. The landlord may decline without consequence, though persistent non-compliance with the spirit of recommendations may feature in later cases.

| Attribute | Type | Description |
|---|---|---|
| `description` | string | Wording of the recommendation |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `contained_in` | Recommendation → | OmbudsmanDecision | 1 |

---

### ComplaintStageResponse

The landlord's formal response at each internal stage of the complaint process before Ombudsman referral. Stage 1 is mandatory; Stage 2 follows if the resident escalates.

| Attribute | Type | Description |
|---|---|---|
| `stage` | enum(`1`, `2`) | Stage 1 = first formal response; Stage 2 = final internal response |
| `acknowledgement_date` | date | Date landlord acknowledged receipt of the complaint / escalation |
| `acknowledgement_days` | int | Working days from complaint / escalation to acknowledgement (Code target: 5 working days) |
| `date_issued` | date | Date landlord issued the full response |
| `response_days` | int | Working days from complaint / escalation receipt to full response |
| `upheld` | bool | Whether landlord upheld the complaint at this stage |
| `compensation_offered` | float | Amount offered by landlord (distinct from any Ombudsman-ordered compensation) |
| `standard_response_days` | int | Complaint Handling Code target for response at this stage (Stage 1 = 10; Stage 2 = 20; reflects the Code version applicable at the decision date) |
| `acknowledgement_exceeded` | bool | `acknowledgement_days > 5` |
| `response_exceeded` | bool | `response_days > standard_response_days` |

**Note on timescales:** The above targets reflect the 2024 statutory Complaint Handling Code. For cases decided before April 2024, earlier (non-statutory) Code versions applied with different timescales. `standard_response_days` should be resolved against the `decision_date` on the parent Case rather than treated as a fixed constant.

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `issued_by_landlord` | ComplaintStageResponse → | Landlord | 1 |
| `part_of` | ComplaintStageResponse → | Case | 1 |

---

### ComplianceRecord

Tracks whether a landlord complied with a specific Order within the required deadline. Central to the Ombudsman's enforcement function.

| Attribute | Type | Description |
|---|---|---|
| `status` | enum(`compliant`, `partial`, `non_compliant`, `pending`) | Compliance outcome |
| `evidence_received_date` | date | Date the landlord provided compliance evidence |
| `notes` | string | Details of compliance or failure |

**Relationships:**

| Predicate | Direction | Target | Cardinality |
|---|---|---|---|
| `records_compliance_with` | ComplianceRecord → | Order | 1 |
| `evidenced_by` | ComplianceRecord → | Landlord | 1 |

---

### Legislation

A statute, approved scheme, statutory code, or regulatory framework cited within an Ombudsman decision. The `legislation_tier` attribute distinguishes legally binding instruments from guidance documents.

| Attribute | Type | Description |
|---|---|---|
| `name` | string | Full name of the instrument |
| `legislation_tier` | enum(`primary`, `secondary`, `approved_scheme`, `statutory_code`, `non_statutory_guidance`) | Legal status of the instrument |
| `citation_context` | enum(`jurisdictional`, `substantive`, `both`) | Whether cited to establish jurisdiction, apply to the facts, or both |

**Key instruments:**

| Instrument | Tier | Context | Notes |
|---|---|---|---|
| Housing Act 1996 | Primary | Both | Jurisdictional via Part X (Ombudsman scheme); substantive via Parts V–VII (tenancies, allocation, homelessness) |
| Housing Ombudsman Scheme | Approved scheme | Jurisdictional | Approved by Secretary of State under Housing Act 1996 s.51; augmented by Social Housing (Regulation) Act 2023 |
| Social Housing (Regulation) Act 2023 | Primary | Both | Introduced statutory Complaint Handling Code, Awaab's Law provisions, and new Ombudsman enforcement powers including CHFOs |
| Complaint Handling Code (2024) | Statutory code | Substantive | Became statutory under Social Housing (Regulation) Act 2023 from 1 April 2024; most-cited instrument in complaint handling determinations |
| Landlord and Tenant Act 1985 | Primary | Substantive | Section 11 (repair covenant); sections 18–30 (service charge reasonableness for leaseholders); amended by the Homes (Fitness for Human Habitation) Act 2018 via sections 9A–9C |
| Housing Act 2004, Part 1 | Primary | Substantive | Statutory basis for the HHSRS operating guidance |
| Housing Health and Safety Rating System (HHSRS) | Non-statutory guidance | Substantive | Operating guidance under Housing Act 2004; not itself a statute; provides the hazard assessment framework for disrepair cases |
| Equality Act 2010 | Primary | Substantive | Disability and vulnerability obligations; Public Sector Equality Duty (s.149) |
| Decent Homes Standard | Non-statutory guidance | Substantive | DLUHC guidance setting a minimum physical condition benchmark; not enforceable as statute |
| Homes (Fitness for Human Habitation) Act 2018 | Primary | Substantive | Amends LTA 1985 by inserting sections 9A–9C (fitness for habitation implied term); often cited via the LTA 1985 as amended |
| Social Housing (Regulation) Act 2023 / Awaab's Law | Primary | Substantive | Provisions in section 42 requiring landlords to investigate and remediate damp and mould within fixed timescales; in force from 27 October 2025 |
| Human Rights Act 1998 | Primary | Substantive | Article 8 (respect for private life and home) |
| Localism Act 2011 | Primary | Substantive | Mutual exchange rights and housing allocation reforms |

---

## Full Predicate Map

```
Resident ──── holds ─────────────────────────────► Tenancy (0..N, is_current flagged)
                                                       │ relates_to
                                                       ▼
Landlord ──── owns_or_manages ─────────────────► Property
         └─── management_structure ────────────► ALMO / TMO (attribute, not entity)

Resident ──── raises ───────────────────────────► Case ◄─── cites ──────► Legislation
                                                    │                         ▲
                              ┌─────────────────────┤                         │
                              │                     │                    governed_by
                         is_against            contains (1..N)               │
                              │                     │                         │
                              ▼                     ▼                         │
                          Landlord              Issue ────────────────────────┘
                                                    │
                                      ┌─────────────┤
                                      │             │
                             has_determination  classified_as
                                      │             │
                                      ▼             ▼
                               Determination    Category
                               (severity scale) (2-tier)

                          [Reasonable Redress — resolution pathway, not on severity scale]

Case ──── has_stage_response ──────────────────► ComplaintStageResponse (Stage 1: 1, Stage 2: 0..1)
                                                    │ offered_compensation_of ──► float

Case ──── results_in ───────────────────────────► OmbudsmanDecision (0..1)
                                                    │
                                       ┌────────────┴──────────────┐
                                  contains_order            contains_recommendation
                                       │                           │
                                       ▼                           ▼
                                    Order (0..N)          Recommendation (0..N)
                                       │
                    [if Compensation]  │
                             compensates_for ──────────────────► Issue

Order ──── has_compliance_record ──────────────► ComplianceRecord
                                                    │ evidenced_by ──► Landlord

Case ──── related_to ───────────────────────────► Case
          (same_property | same_resident | same_defect | follow_on)
```

---

## Process Flow (Temporal)

```
1. INCIDENT
   Resident reports defect / ASB to Landlord
   (may repeat over months or years; each report is date-stamped)

2. LANDLORD ACTION
   Contractor visits, surveys, access attempts, works scheduled

3. COMPLAINT RAISED — Stage 1
   Landlord must: acknowledge within 5 working days
                  log the complaint within 5 working days
                  respond within 10 working days
   (Complaint Handling Code 2024, statutory from 1 April 2024)

4. STAGE 1 RESPONSE
   Landlord upholds / partially upholds / rejects
   May offer compensation; resident may accept or escalate

5. ESCALATION — Stage 2
   Landlord must: acknowledge within 5 working days
                  respond within 20 working days

6. STAGE 2 FINAL RESPONSE
   Landlord's final internal position

7. REFERRAL TO OMBUDSMAN
   Resident refers case; Ombudsman assesses jurisdiction

8. INTAKE / JURISDICTION ASSESSMENT  ← [Case.intake_outcome set here]
   The Ombudsman determines:
   a) Accept for investigation  → proceed to step 9
   b) Outside jurisdiction      → Case closed (no Issues, no Decision)
   c) Refer back to landlord    → internal process not exhausted
   d) Early resolution pathway  → landlord invited to settle
      └── Landlord offers remedy → Ombudsman satisfied → Reasonable Redress
                                → Ombudsman not satisfied → proceed to step 9

9. INVESTIGATION
   Evidence reviewed from both parties
   Landlord may make further offers during this phase
   A CHFO may be issued if landlord fails to engage with the investigation

10. DECISION PUBLISHED
    Determination per Issue (findings on the severity scale, or Reasonable Redress)
    Orders (binding) and Recommendations (non-binding) issued with due dates

11. COMPLIANCE
    Landlord evidences compliance with each Order within the due date
    Non-compliance recorded in ComplianceRecord
    Persistent non-compliance may be escalated to the Regulator of Social Housing
```

---

## Key Ontological Patterns

### Pattern 1: Process Failure is Orthogonal to Substantive Failure

A damp case will almost always carry a Complaint Handling issue alongside it. These are independent axes:
- **Substantive axis**: What went wrong with the property or service?
- **Process axis**: How well did the landlord handle the complaint about it?

A finding of Maladministration on Complaint Handling does not imply any particular finding on the substantive issue, and vice versa.

### Pattern 2: Severity × Persistence × Impact

The three dimensions that distinguish Maladministration from Severe Maladministration:
- **Severity** — how serious was the failure itself?
- **Persistence** — was it isolated or repeated over an extended period?
- **Impact** — what harm did it cause the resident, especially where the resident is vulnerable?

Compensation awards reflect all three. Rehousing failures under Severe Maladministration command significantly larger awards than Complaint Handling failures, reflecting the gravity of denying housing access.

### Pattern 3: Landlord Type and Management Structure Moderate Outcomes

Local Authorities and Housing Associations operate under different legal frameworks (secure tenancy vs. assured tenancy) with different statutory repair obligations, allocation duties, and regulatory accountability structures. Where an ALMO or TMO manages stock, responsibility in Ombudsman decisions typically attaches to the stock-owning authority, not the management organisation.

### Pattern 4: Vulnerability Amplifies Awards

Resident vulnerability is a consistent amplifier. Cases involving unresolved damp affecting a resident with a respiratory condition, or ASB affecting children, typically receive higher severity determinations and larger compensation orders. Vulnerability is not a separate legal threshold — it is an aggravating factor in the Ombudsman's assessment of impact under the Equality Act 2010.

### Pattern 5: Legal Instrument Tier Determines Analytical Weight

- **Jurisdictional anchors** (Housing Ombudsman Scheme, Housing Act 1996 Part X): present in the vast majority of decisions as boilerplate; low discriminatory signal
- **Substantive repair/condition instruments** (LTA 1985 s.11, HHSRS, Awaab's Law): high signal for Damp & Mould, Repairs, and Building Safety cases
- **Equality and vulnerability instruments** (Equality Act 2010, s.149 PSED): high signal for cases involving vulnerability amplification
- **Process instruments** (Complaint Handling Code 2024, statutory): high signal for Complaint Handling findings; the most-cited instrument after the jurisdictional boilerplate
- **Non-statutory guidance** (Decent Homes Standard, HHSRS operating guidance): cited as benchmarks, not as enforceable standards; landlord failure to apply them is evidence of poor practice, not a direct legal breach

### Pattern 6: Reasonable Redress Sits Outside the Severity Scale

`Reasonable Redress` is not a severity finding. It is a resolution pathway that closes a case when the landlord has offered a proportionate remedy. The underlying conduct may have warranted Maladministration or Severe Maladministration had it not been remedied. Placing it on the same axis as No Maladministration → Severe Maladministration misrepresents what it measures. In analysis, Reasonable Redress cases should be grouped separately from both upheld and not-upheld findings.
