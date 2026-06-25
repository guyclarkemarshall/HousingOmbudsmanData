# Domain Glossary

This glossary acts as a translation bridge between social housing operations and codebase database models.

| Term | Definition | Where Used in Code | Notes |
|------|------------|-------------------|-------|
| **Maladministration** | A finding by the Ombudsman that the landlord failed to act in accordance with its policies, law, or fair service. | `issues.determination` | Upheld finding |
| **Severe Maladministration** | The most serious finding of service failure by the Ombudsman, indicating systemic neglect, delay, or failure to act. | `issues.determination` | Upheld finding |
| **Service Failure** | A finding that the landlord's action or inaction amounted to a failure of service (less severe than Maladministration). | `issues.determination` | Upheld finding |
| **Reasonable Redress** | A finding that while the landlord failed initially, they resolved the issue and offered reasonable remedy prior to the Ombudsman investigation. | `issues.determination` | Not classified as upheld |
| **No Maladministration** | A finding that the landlord acted correctly and in accordance with service standards. | `issues.determination` | Not upheld |
| **Damp & Mould** | Problems related to condensation, moisture ingress, and fungal growth. | `issues.category` | Key focus area under Awaab's Law |
| **ASB** | Anti-Social Behaviour. Disputes involving neighborhood harassment, noise, or safety. | `issues.category` | Commonly handled by housing officers |
| **Void** | An empty property between tenancies undergoing repairs. | `cases.tenancy_type` (in some preambles) | Often referred to as "void management" |
| **UPRN** | Unique Property Reference Number. A 12-digit standard identifier for land/property in the UK. | `cases` (referred in planning) | Crucial standard for cross-landlord data mapping |
| **Tenure** | The legal arrangement under which a resident occupies their home (e.g. Secure Tenancy, Assured Tenancy, Leaseholder). | `cases.tenancy_type` | Crucial context; leaseholders have different rights than secure tenants |
| **Apology Ordered** | An Ombudsman order requiring the landlord to issue a formal written apology to the resident. | `cases.apology_ordered_est` | Heuristic tracking |
| **Repairs Ordered** | An Ombudsman order requiring the landlord to complete outstanding maintenance work. | `cases.repairs_ordered_est` | Heuristic tracking |
