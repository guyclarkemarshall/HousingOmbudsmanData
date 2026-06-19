# UK Housing Ombudsman Disputes Dataset

A robust and complete dataset of housing dispute decisions scraped from the UK Housing Ombudsman's public index, stored in a local SQLite database.

## Dataset Overview

The dataset contains **16,611** extracted housing dispute decisions covering cases processed from 2019 up to mid-2026. Two database packages are provided:

1. **Unstructured Decisions Database**: `ombudsman_decisions.zip` (compressed to 87 MB from the original 342.5 MB SQLite `.db` file).
2. **Relational Insights Database**: `ombudsman_insights.zip` (compressed to 91 MB from the original 358 MB SQLite `.db` file). Built using text heuristics to support analytical querying, compliance mapping, and predictive modeling.

- **URLs List**: `urls.txt` contains the complete set of 16,612 harvested decision detail URLs.

---

## Licensing & Attribution

This dataset is distributed under the **Creative Commons Attribution 4.0 International (CC-BY-4.0)** license. See the [LICENSE](file:///c:/Users/guycl/OmbudsmanScraper/LICENSE) file for details.

### Source Acknowledgment
- **Source**: All raw decision reports are sourced directly from the [UK Housing Ombudsman website](https://www.housing-ombudsman.org.uk/decisions/).
- **Original License**: Original materials published by the UK Housing Ombudsman are subject to Crown Copyright and published under the **Open Government Licence v3.0 (OGL-3.0)**.
- **Attribution Statement**: Contains public sector information licensed under the Open Government Licence v3.0. Sourced from the UK Housing Ombudsman.

If you use or redistribute this dataset, you must attribute the work by retaining the notice above and citing this repository.

---

## Relational Insights Database (`ombudsman_insights.db`)

This database compiles unstructured text fields into structured, normalized relational tables.

### Table Schema

```mermaid
erDiagram
    landlords ||--o{ cases : "resolves"
    cases ||--o{ issues : "contains"
    cases ||--o{ compensation_orders : "orders"

    landlords {
        int id PK
        string name UNIQUE
    }

    cases {
        int id PK
        string case_id UNIQUE
        string url
        string title
        string decision_date
        int landlord_id FK
        float total_compensation_ordered
        int stage_1_days_est
        int stage_2_days_est
        int timescales_exceeded_est
        int is_upheld_est
        int apology_ordered_est
        int repairs_ordered_est
        int review_or_training_ordered_est
        int vulnerability_mentioned_est
        int communication_failure_est
        int record_keeping_failure_est
        string full_text
    }

    issues {
        int id PK
        string case_id FK
        string description
        string determination
        string category
        int is_upheld_est
    }

    compensation_orders {
        int id PK
        string case_id FK
        float amount
        string description
    }
```

#### 1. `landlords`
Lookup table containing unique names of the social landlords/local authorities involved.
* `id` (INTEGER, PK): Auto-incremented identifier.
* `name` (TEXT, UNIQUE): Cleaned landlord name.

#### 2. `cases`
The main case record table containing overall complaint characteristics and outcomes:
* `case_id` (TEXT, PK): Unique Ombudsman case number (e.g. `202113360`).
* `url` (TEXT): Source decision page URL.
* `title` (TEXT): Full case title header.
* `decision_date` (TEXT): Date of the ombudsman decision.
* `landlord_id` (INTEGER, FK): Reference to `landlords(id)`.
* `total_compensation_ordered` (REAL): Sum of all financial compensation orders within the case.
* `stage_1_days_est` / `stage_2_days_est` (INTEGER): Estimated days taken by the landlord to resolve the complaint at Stage 1 / Stage 2 of their internal process.
* `timescales_exceeded_est` (INTEGER): Binary indicator (1 = exceeded, 0 = within standards, NULL = unknown) based on compliance language in the text.
* `is_upheld_est` (INTEGER): `1` (True) if the landlord was found responsible for maladministration, severe maladministration, or service failure in any of the case's issues; `0` otherwise.
* `apology_ordered_est` (INTEGER): `1` if the landlord was ordered by the Ombudsman to apologize in writing to the resident; `0` otherwise.
* `repairs_ordered_est` (INTEGER): `1` if the landlord was ordered to complete repairs, damp surveys, or works; `0` otherwise.
* `review_or_training_ordered_est` (INTEGER): `1` if the landlord was ordered to review its policies, procedures, or undergo staff training; `0` otherwise.
* `vulnerability_mentioned_est` (INTEGER): `1` if resident vulnerability factors (health, disability, mental health, age, children) were noted in the text; `0` otherwise.
* `communication_failure_est` (INTEGER): `1` if the case notes poor communication, failure to update, or ignoring the tenant; `0` otherwise.
* `record_keeping_failure_est` (INTEGER): `1` if the case notes poor record-keeping, missing files, or inadequate documentation; `0` otherwise.
* `full_text` (TEXT): Full text of the raw Ombudsman decision report.

#### 3. `issues`
Granular issue-level determinations parsed from the Ombudsman's decision text:
* `case_id` (TEXT, FK): Reference to `cases(case_id)`.
* `description` (TEXT): Context sentence containing the issue and determination.
* `determination` (TEXT): Standardized outcome (`Severe Maladministration`, `Maladministration`, `Service Failure`, `Reasonable Redress`, `No Maladministration`, `Outside Jurisdiction`).
* `category` (TEXT): Classified dispute category (`Damp & Mould`, `Leaks & Water Ingress`, `Anti-Social Behaviour (ASB)`, `Complaint Handling`, `Pest Control`, `Rent & Service Charges`, `Estate Management`, `Repairs & Maintenance`, `Other`).
* `is_upheld_est` (INTEGER): `1` if the specific issue is upheld (Maladministration, Severe Maladministration, Service Failure); `0` otherwise.

#### 4. `compensation_orders`
Individual financial awards ordered by the Ombudsman.
* `case_id` (TEXT, FK): Reference to `cases(case_id)`.
* `amount` (REAL): Numeric award amount in British Pounds (£).
* `description` (TEXT): Excerpt from the order detailing what the award compensates.

---

## Dataset Insights & Statistics

Running the validation check on `ombudsman_insights.db` yields the following summaries:

* **Record Counts**:
  * Landlords: 723
  * Cases: 16,611
  * Issue-level Determinations: 40,896
  * Compensation Orders: 30,755

* **Complaint Upheld Rates**:
  * **Overall Upheld Cases**: **71.6%** (11,896 out of 16,611 cases had at least one finding of failure against the landlord).
  * **Overall Upheld Issues**: **60.9%** (24,897 out of 40,896 issue determinations upheld).
  * **Upheld Rate by Dispute Category**:
    * Damp & Mould: **77.2%** (2,038 / 2,639)
    * Leaks & Water Ingress: **67.7%** (1,360 / 2,010)
    * Complaint Handling: **60.7%** (15,191 / 25,008)
    * Pest Control: **59.5%** (22 / 37)
    * Anti-Social Behaviour (ASB): **56.9%** (1,322 / 2,325)
    * Repairs & Maintenance: **55.9%** (179 / 320)
    * Rent & Service Charges: **52.5%** (1,020 / 1,944)
    * Estate Management: **44.8%** (91 / 203)
    * Other: **57.3%** (3,674 / 6,410)

* **Ombudsman Remedies & Orders (Case Level)**:
  * **Repairs/Works Ordered**: **42.2%** (7,002 cases)
  * **Apologies Ordered**: **23.7%** (3,941 cases)
  * **Policy/Training Reviews Ordered**: **22.3%** (3,702 cases)

* **Operational Failures & Context (Case Level)**:
  * **Vulnerability Mentioned**: **73.9%** (12,280 cases)
  * **Communication Failures**: **36.1%** (5,997 cases)
  * **Record Keeping Failures**: **13.1%** (2,174 cases)

* **Complaint Timescales & Standards**:
  * Average Stage 1 Response Time: **13.3 working days** (compliant standard under the Complaint Handling Code is 10 working days).
  * Average Stage 2 Response Time: **22.4 working days** (compliant standard is 20 working days).
  * Exceeded standards rate: **40.6%** of cases with classified timescale compliance language.

* **Financial Compensation**:
  * Total Compensation Ordered: **£14,090,950.00**
  * Cases with Ordered Compensation: **49.4%**
  * Average Compensation (where ordered): **£1,718.20**
  * Maximum Single Case Compensation: **£86,831.00** (awarded to a tenant of Hackney Council).

---

## How to Use the Data

### 1. Extract the Databases
Since both SQLite database files exceed GitHub's single-file limit, they are stored as compressed zip archives.

*On Windows (PowerShell):*
```powershell
# Extract decisions database
Expand-Archive -Path ombudsman_decisions.zip -DestinationPath .
# Extract relational insights database
Expand-Archive -Path ombudsman_insights.zip -DestinationPath .
```

*On Linux/macOS:*
```bash
unzip ombudsman_decisions.zip
unzip ombudsman_insights.zip
```

### 2. Analytical Queries (Python Sample)
You can analyze patterns or train models on the structured data easily:

```python
import sqlite3

conn = sqlite3.connect("ombudsman_insights.db")
cursor = conn.cursor()

# Query the average compensation ordered for Damp & Mould issues by landlord
cursor.execute("""
    SELECT landlords.name, COUNT(cases.id) as case_count, AVG(cases.total_compensation_ordered) as avg_comp
    FROM cases
    JOIN landlords ON cases.landlord_id = landlords.id
    JOIN issues ON cases.case_id = issues.case_id
    WHERE issues.category = 'Damp & Mould'
    GROUP BY landlords.name
    HAVING case_count >= 10
    ORDER BY avg_comp DESC
    LIMIT 5
""")

print("Top 5 landlords by average compensation for Damp & Mould cases:")
for row in cursor.fetchall():
    print(f"Landlord: {row[0]:<40} | Cases: {row[1]:>3} | Avg Comp: £{row[2]:.2f}")

conn.close()
```

---

## Running the Scraper

The repository includes the scraping utility [scraper.py](file:///c:/Users/guycl/OmbudsmanScraper/scraper.py). If you want to update the database or re-scrape decisions, you can use the script directly.

### Prerequisites
Install the required packages:
```bash
pip install requests beautifulsoup4
```

### Script Arguments
- `--harvest`: Run Phase 1 to harvest decision URLs from index.
- `--extract`: Run Phase 2 to extract decision content from harvested URLs.
- `--start-page`: Start page for URL harvesting.
- `--end-page`: End page for URL harvesting.
- `--db`: SQLite database filename (default: `ombudsman_decisions.db`).
- `--urls-file`: Text file to save/read URLs (default: `urls.txt`).

### Examples
*Harvest the first 5 archive pages:*
```bash
python scraper.py --harvest --start-page 1 --end-page 5
```

*Extract content for all URLs currently listed in `urls.txt`:*
```bash
python scraper.py --extract
```
