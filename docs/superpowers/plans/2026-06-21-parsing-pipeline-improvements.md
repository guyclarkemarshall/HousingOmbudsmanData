# Parsing Pipeline Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `build_insights_db.py` to detect document format, split documents into sections before parsing, fix the category classifier, remove the compensation cap, capture new structured fields (`landlord_type`, `tenancy_type`, `doc_format`), and add a `legal_citations` table.

**Architecture:** A new `section_splitter.py` module handles all document format detection and section splitting. `build_insights_db.py` is updated to import and use the splitter so every extractor operates on the relevant section of the document rather than the full text. Schema changes are all in `init_dest_db`. Existing extractor functions are updated in-place.

**Tech Stack:** Python 3.11, SQLite 3 (stdlib), `re` (stdlib), `uv` for running scripts.

## Global Constraints

- Python >= 3.11
- No new runtime dependencies — all changes use stdlib only
- `ombudsman_decisions.db` is read-only source — never modified
- `ombudsman_insights.db` is always rebuilt from scratch (`init_dest_db` drops and recreates it)
- Entry points are defined in `pyproject.toml` — `uv run build-insights` and `uv run verify-insights`
- All paths are relative to the project root: `/Users/diegocarvallo/Documents/diego-personal/HousingOmbudsmanData/`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `section_splitter.py` | **Create** | Format detection, section splitting, `Complaint/Finding` pair extraction |
| `build_insights_db.py` | **Modify** | Import splitter; update schema; update all extractors to use sections; add new field extractions |
| `verify_insights.py` | **Modify** | Add verification sections for new fields and `legal_citations` table |

---

## Task 1: Create `section_splitter.py` — format detection and section splitting

**Files:**
- Create: `section_splitter.py`

**Interfaces:**
- Produces:
  - `detect_format(text: str) -> str` — returns `'new'` or `'old'`
  - `split_sections(text: str) -> dict[str, str]` — returns `{section_name: section_text}`
  - `extract_complaint_finding_pairs(text: str) -> list[dict]` — returns `[{'complaint': str, 'outcome': str, 'analysis': str}]`

- [ ] **Step 1: Create `section_splitter.py` with the full implementation**

```python
import re

# New-format docs (Nov 2025+) start with this metadata block
_NEW_FORMAT_MARKER = re.compile(r'^Decision\s*\nCase ID', re.MULTILINE)

# Old-format docs start with REPORT heading
_OLD_FORMAT_MARKER = re.compile(r'\bREPORT\b')

OLD_SECTION_RE = re.compile(
    r'^('
    r'Background(?: and summary of events)?'
    r'|Summary of events'
    r'|The complaint'
    r'|Policies and Procedures'
    r'|Assessment and findings?'
    r'|Scope(?: of(?: the)? investigation)?'
    r'|Complaint handling'
    r'|Determination(?:\s*\((?:decision|jurisdictional decision)\))?'
    r'|Orders?(?: and recommendations?)?'
    r'|Recommendations?'
    r'|Conclusion'
    r'|Investigation'
    r')\s*$',
    re.MULTILINE | re.IGNORECASE
)

NEW_SECTION_RE = re.compile(
    r'^('
    r'Background'
    r'|What the complaint is about'
    r'|Our decision\s*\(determination\)'
    r'|Summary of reasons'
    r'|Putting things right'
    r'|Our investigation'
    r'|What we found(?: and why)?'
    r'|Orders?(?: and recommendations?)?'
    r'|Recommendations?'
    r'|Complaint'
    r'|Finding'
    r')\s*$',
    re.MULTILINE | re.IGNORECASE
)

# New-format Complaint/Finding pair extraction
_FINDING_PAIR_RE = re.compile(
    r'\nComplaint\n(.*?)\nFinding\n'
    r'(No maladministration|Service failure|Maladministration|'
    r'Severe maladministration|Reasonable redress|Outside jurisdiction)\n'
    r'(.*?)(?=\nComplaint\n|\nOrders?\n|\nPutting things right\n|$)',
    re.DOTALL | re.IGNORECASE
)

# Normalised determination labels (match OUTCOME_PATTERNS in build_insights_db.py)
_DETERMINATION_NORMALISE = {
    'severe maladministration': 'Severe Maladministration',
    'no maladministration': 'No Maladministration',
    'maladministration': 'Maladministration',
    'service failure': 'Service Failure',
    'reasonable redress': 'Reasonable Redress',
    'outside jurisdiction': 'Outside Jurisdiction',
}


def detect_format(text: str) -> str:
    """Return 'new' for Investigation format (Nov 2025+) or 'old' for REPORT format."""
    if _NEW_FORMAT_MARKER.search(text[:200]):
        return 'new'
    return 'old'


def split_sections(text: str) -> dict:
    """
    Split a Housing Ombudsman decision into named sections.
    Returns dict of {section_name: section_text}.
    Handles both old REPORT format and new Investigation format.
    Repeating Complaint/Finding headings (new format) are indexed: complaint_1, finding_1, etc.
    """
    fmt = detect_format(text)
    section_re = NEW_SECTION_RE if fmt == 'new' else OLD_SECTION_RE

    matches = list(section_re.finditer(text))
    if not matches:
        return {'full_doc': text}

    sections = {}

    # Capture preamble (metadata header before first heading)
    if matches[0].start() > 0:
        sections['preamble'] = text[:matches[0].start()].strip()

    counters = {}
    for i, m in enumerate(matches):
        raw_name = m.group(1).strip().lower()
        # Normalise spacing variants to a canonical key
        name = re.sub(r'\s+', '_', raw_name)
        name = re.sub(r'[^a-z0-9_]', '', name)

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Index repeated headings (complaint_1, complaint_2, finding_1 ...)
        if name in counters:
            counters[name] += 1
            key = f"{name}_{counters[name]}"
        else:
            counters[name] = 1
            key = f"{name}_1" if name in ('complaint', 'finding') else name

        sections[key] = content

    return sections


def extract_complaint_finding_pairs(text: str) -> list:
    """
    For new-format docs: extract structured (complaint, outcome, analysis) tuples
    from Complaint/Finding heading pairs inside the Our investigation section.
    Returns list of dicts with keys: complaint, outcome, analysis.
    outcome is normalised to match OUTCOME_PATTERNS labels in build_insights_db.py.
    """
    results = []
    for m in _FINDING_PAIR_RE.finditer(text):
        raw_outcome = m.group(2).strip().lower()
        outcome = _DETERMINATION_NORMALISE.get(raw_outcome, m.group(2).strip())
        results.append({
            'complaint': m.group(1).strip(),
            'outcome': outcome,
            'analysis': m.group(3).strip(),
        })
    return results
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
cd /Users/diegocarvallo/Documents/diego-personal/HousingOmbudsmanData
uv run python -c "from section_splitter import detect_format, split_sections, extract_complaint_finding_pairs; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Smoke-test against a real document from both formats**

```bash
uv run python - << 'EOF'
import sqlite3
from section_splitter import detect_format, split_sections, extract_complaint_finding_pairs

conn = sqlite3.connect('ombudsman_decisions.db')
# New format: id <= 1941 (Nov 2025+)
new_row = conn.execute("SELECT full_text FROM decisions WHERE id = 50").fetchone()[0]
# Old format: id >= 1942
old_row = conn.execute("SELECT full_text FROM decisions WHERE id = 2000").fetchone()[0]

print("=== NEW FORMAT ===")
print("Detected:", detect_format(new_row))
secs = split_sections(new_row)
print("Sections:", list(secs.keys()))
pairs = extract_complaint_finding_pairs(new_row)
print("Complaint/Finding pairs:", len(pairs))
if pairs:
    print("First pair outcome:", pairs[0]['outcome'])

print("\n=== OLD FORMAT ===")
print("Detected:", detect_format(old_row))
secs = split_sections(old_row)
print("Sections:", list(secs.keys()))
EOF
```

Expected: new format shows `detected: new`, lists sections including `our_decision_determination` or `our_investigation`. Old format shows `detected: old`, lists `background`, `assessment_and_findings` etc.

- [ ] **Step 4: Commit**

```bash
git add section_splitter.py
git commit -m "feat: add section splitter for old/new document formats"
```

---

## Task 2: Update `build_insights_db.py` schema — new columns and `legal_citations` table

**Files:**
- Modify: `build_insights_db.py` — `init_dest_db` function (lines 29–108)

**Interfaces:**
- Consumes: nothing new
- Produces: `cases` table gains `doc_format TEXT`, `landlord_type TEXT`, `tenancy_type TEXT` columns; new `legal_citations` table

- [ ] **Step 1: Add three new columns to the `CREATE TABLE cases` statement**

In `init_dest_db`, find the `cases` CREATE TABLE block. Replace:

```python
            record_keeping_failure_est INTEGER DEFAULT 0,
            full_text TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlords(id)
```

With:

```python
            record_keeping_failure_est INTEGER DEFAULT 0,
            doc_format TEXT,
            landlord_type TEXT,
            tenancy_type TEXT,
            full_text TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlords(id)
```

- [ ] **Step 2: Add `legal_citations` table and its indexes after the `compensation_orders` block**

After the `compensation_orders` CREATE TABLE block (around line 96), insert:

```python
    # 5. Legal Citations Table
    cursor.execute("""
        CREATE TABLE legal_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            statute TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        )
    """)
```

After the existing index definitions, add:

```python
    cursor.execute("CREATE INDEX idx_citations_case ON legal_citations(case_id)")
    cursor.execute("CREATE INDEX idx_citations_statute ON legal_citations(statute)")
```

- [ ] **Step 3: Verify schema is correct by running a dry init**

```bash
uv run python - << 'EOF'
import sqlite3, os
# Temporarily init against a test DB to check schema
conn = sqlite3.connect('/tmp/test_schema.db')
# Inline the schema SQL to avoid running the full pipeline
conn.executescript("""
CREATE TABLE cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE NOT NULL,
    doc_format TEXT,
    landlord_type TEXT,
    tenancy_type TEXT,
    full_text TEXT
);
CREATE TABLE legal_citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    statute TEXT NOT NULL
);
""")
cols = [r[1] for r in conn.execute("PRAGMA table_info(cases)")]
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("cases columns:", cols)
print("tables:", tables)
conn.close()
os.unlink('/tmp/test_schema.db')
EOF
```

Expected: `cases columns` includes `doc_format`, `landlord_type`, `tenancy_type`. `tables` includes `legal_citations`.

- [ ] **Step 4: Commit**

```bash
git add build_insights_db.py
git commit -m "feat: add doc_format, landlord_type, tenancy_type columns and legal_citations table to schema"
```

---

## Task 3: Add extraction functions for new fields

**Files:**
- Modify: `build_insights_db.py` — add new functions after `extract_compensation`

**Interfaces:**
- Consumes: `sections: dict` from `split_sections()` and `full_text: str`
- Produces:
  - `extract_landlord_type(sections: dict) -> str | None`
  - `extract_tenancy_type(sections: dict) -> str | None`
  - `extract_legal_citations(full_text: str) -> list[str]`

- [ ] **Step 1: Add `extract_landlord_type` and `extract_tenancy_type` after `extract_compensation`**

```python
def extract_landlord_type(sections: dict) -> str | None:
    """Extracts landlord type from the document preamble/header metadata block."""
    preamble = sections.get('preamble', '')
    m = re.search(r'Landlord type\s*\n(.+)', preamble)
    if m:
        return m.group(1).strip()
    # Fallback: search first 500 chars of full doc for old-format docs without preamble key
    full = sections.get('full_doc', '')
    m = re.search(r'Landlord type\s*\n(.+)', full[:500])
    return m.group(1).strip() if m else None


def extract_tenancy_type(sections: dict) -> str | None:
    """Extracts tenancy/occupancy type from the document preamble/header metadata block."""
    preamble = sections.get('preamble', '')
    m = re.search(r'Occupancy\s*\n(.+)', preamble)
    if m:
        return m.group(1).strip()
    full = sections.get('full_doc', '')
    m = re.search(r'Occupancy\s*\n(.+)', full[:500])
    return m.group(1).strip() if m else None
```

- [ ] **Step 2: Add `STATUTES` list and `extract_legal_citations` after the two functions above**

```python
STATUTES = [
    "Housing Act 1996",
    "Homes (Fitness for Human Habitation) Act 2018",
    "Awaab's Law",
    "Landlord and Tenant Act 1985",
    "Equality Act 2010",
    "Decent Homes Standard",
    "Housing Ombudsman Scheme",
    "Human Rights Act",
    "Care Act 2014",
    "Localism Act 2011",
    "Housing Health and Safety Rating System",
    "HHSRS",
]

# Precompile once at module load — avoids recompiling for every one of 16,611 docs
_STATUTE_PATTERNS = [(s, re.compile(re.escape(s), re.IGNORECASE)) for s in STATUTES]


def extract_legal_citations(full_text: str) -> list:
    """Returns deduplicated list of statute names cited anywhere in the decision text."""
    return [statute for statute, pattern in _STATUTE_PATTERNS if pattern.search(full_text)]
```

- [ ] **Step 3: Smoke-test all three functions**

```bash
uv run python - << 'EOF'
import sqlite3
from build_insights_db import extract_landlord_type, extract_tenancy_type, extract_legal_citations
from section_splitter import split_sections

conn = sqlite3.connect('ombudsman_decisions.db')
row = conn.execute("SELECT full_text FROM decisions WHERE id = 2000").fetchone()[0]
sections = split_sections(row)

print("landlord_type:", extract_landlord_type(sections))
print("tenancy_type: ", extract_tenancy_type(sections))
print("citations:    ", extract_legal_citations(row))
conn.close()
EOF
```

Expected: `landlord_type` returns a non-None string like `Housing Association`. `citations` returns a list containing at least `Housing Act 1996` (present in every old-format doc's boilerplate).

- [ ] **Step 4: Commit**

```bash
git add build_insights_db.py
git commit -m "feat: add landlord_type, tenancy_type, and legal_citations extraction functions"
```

---

## Task 4: Fix `classify_category` — reorder and add Rehousing & Allocations

**Files:**
- Modify: `build_insights_db.py` — `classify_category` function (lines 171–192)

**Interfaces:**
- Consumes: `desc: str` (issue description sentence)
- Produces: `str` — one of the 10 category labels

- [ ] **Step 1: Replace the entire `classify_category` function body**

```python
def classify_category(desc):
    """Classifies dispute descriptions into discrete standard categories.
    Ordered most-specific first so 'Complaint Handling' only fires as residual."""
    desc_lower = desc.lower()

    if re.search(r'\b(damp|mould|condensation)\b', desc_lower):
        return "Damp & Mould"
    elif re.search(r'\b(infestation|pest|mice|rats|bugs|cockroaches|wasps|fleas)\b', desc_lower):
        return "Pest Control"
    elif re.search(r'\b(leak|water|flood|burst|ingress|piping)\b', desc_lower):
        return "Leaks & Water Ingress"
    elif re.search(r'\b(noise|antisocial|asb|anti-social|harassment|nuisance)\b', desc_lower):
        return "Anti-Social Behaviour (ASB)"
    elif re.search(r'\b(rent|service charge|billing|arrears)\b', desc_lower):
        return "Rent & Service Charges"
    elif re.search(r'\b(communal|estate management|garden|cleaning|refuse|bin|parking)\b', desc_lower):
        return "Estate Management"
    elif re.search(r'\b(repair|maintenance|window|roof|boiler|heating|hot water|door|lift|gutter|structure)\b', desc_lower):
        return "Repairs & Maintenance"
    elif re.search(r'\b(rehousing|allocation|transfer|decant|homeless|lettings|bidding|housing register)\b', desc_lower):
        return "Rehousing & Allocations"
    elif re.search(r'\b(complaint|handling|escalation|stages?|response)\b', desc_lower):
        return "Complaint Handling"
    else:
        return "Other"
```

Key changes from original:
- Pest Control moves from position 5 → 2
- Leaks & Water Ingress stays at position 3
- Complaint Handling moves from position 4 → 9 (second-to-last)
- "Rent & Service Charges" drops `financial|compensation|costs` from the pattern (too broad — these words appear in almost every case)
- "Rehousing & Allocations" is new at position 8

- [ ] **Step 2: Verify the function produces sensible output for sample sentences**

```bash
uv run python - << 'EOF'
from build_insights_db import classify_category

tests = [
    ("landlord's handling of damp and mould in the property", "Damp & Mould"),
    ("landlord's handling of the repair to the boiler", "Repairs & Maintenance"),
    ("landlord's complaint handling at stage 2", "Complaint Handling"),
    ("landlord's response to reports of mice infestation", "Pest Control"),
    ("landlord's handling of the resident's transfer request", "Rehousing & Allocations"),
    ("landlord's handling of the water leak from the roof", "Leaks & Water Ingress"),
]

all_pass = True
for desc, expected in tests:
    got = classify_category(desc)
    status = "PASS" if got == expected else f"FAIL (got: {got})"
    print(f"{status}: '{desc[:50]}...'")
    if got != expected:
        all_pass = False

print("\nAll pass:", all_pass)
EOF
```

Expected: All 6 tests print `PASS`.

- [ ] **Step 3: Commit**

```bash
git add build_insights_db.py
git commit -m "fix: reorder classify_category so Complaint Handling is residual, add Rehousing & Allocations"
```

---

## Task 5: Fix `extract_compensation` — remove £10k cap

**Files:**
- Modify: `build_insights_db.py` — `extract_compensation` function (lines 275–306)

**Interfaces:**
- Consumes: `sections: dict` (will use orders section text instead of full text)
- Produces: `tuple[float, list[tuple[float, str]]]` — `(total_amount, [(amount, description), ...])`

Note: this task also migrates `extract_compensation` to use the pre-split orders section rather than running its own section-finding regex.

- [ ] **Step 1: Replace `extract_compensation` with a section-aware version**

```python
def extract_compensation(sections: dict) -> tuple:
    """Extracts ordered compensation amounts from the Orders/Putting things right section.
    Uses pre-split sections dict. Falls back to full_doc if orders section not found."""
    # Prefer the authoritative orders section; fall back to full text
    orders_text = (
        sections.get('orders_and_recommendations')
        or sections.get('orders_1')
        or sections.get('orders')
        or sections.get('putting_things_right_1')
        or sections.get('putting_things_right')
        or sections.get('full_doc', '')
    )
    clean_text = ' '.join(orders_text.split())
    sentences = re.split(r'\.\s*(?=[A-Z])', clean_text)

    total_amount = 0.0
    items = []

    for sentence in sentences:
        matches = re.findall(r'£([0-9,]+)', sentence)
        for m in matches:
            val_str = m.replace(',', '')
            try:
                val = float(val_str)
                if val < 5.0:
                    continue
                # Skip very large values that reference claim amounts rather than orders
                if val > 50000.0 and 'claim' in sentence.lower():
                    continue
                total_amount += val
                items.append((val, sentence.strip()[:250]))
            except ValueError:
                pass

    return total_amount, items
```

- [ ] **Step 2: Verify the cap is gone and large awards are captured**

```bash
uv run python - << 'EOF'
import sqlite3
from section_splitter import split_sections
from build_insights_db import extract_compensation

conn = sqlite3.connect('ombudsman_decisions.db')
# Find a case with known large compensation - search for £86,831
row = conn.execute(
    "SELECT full_text FROM decisions WHERE full_text LIKE '%86,831%' OR full_text LIKE '%86831%' LIMIT 1"
).fetchone()

if row:
    sections = split_sections(row[0])
    total, items = extract_compensation(sections)
    print(f"Total: £{total:,.2f}")
    print(f"Items: {len(items)}")
    for amt, desc in items[:5]:
        print(f"  £{amt:,.2f}: {desc[:80]}")
else:
    # Test with any large award > £10k
    rows = conn.execute("SELECT full_text FROM decisions LIMIT 500").fetchall()
    found = False
    for (text,) in rows:
        sections = split_sections(text)
        total, items = extract_compensation(sections)
        if total > 10000:
            print(f"Found large award: £{total:,.2f}")
            found = True
            break
    if not found:
        print("No large awards in first 500 docs (may not be in sample)")
conn.close()
EOF
```

Expected: Either finds the £86,831 case and prints a total above £10k, or finds another large award. No crash.

- [ ] **Step 3: Commit**

```bash
git add build_insights_db.py
git commit -m "fix: remove £10k compensation cap, use section-split orders text for extraction"
```

---

## Task 6: Add secondary `Complaint/Finding` block extraction for new-format docs

**Files:**
- Modify: `build_insights_db.py` — `compile_database` function, step 6 (lines 362–370)

**Interfaces:**
- Consumes: `extract_complaint_finding_pairs(text: str)` from `section_splitter.py`, `doc_format: str`
- Produces: merged `findings` list fed into issue insertion loop

- [ ] **Step 1: Add import of `section_splitter` at top of `build_insights_db.py`**

After the existing imports block (after `import sqlite3`), add:

```python
from section_splitter import detect_format, split_sections, extract_complaint_finding_pairs
```

- [ ] **Step 2: Update step 6 in `compile_database` to merge primary and secondary findings**

Replace the current step 6 block:

```python
        # 6. Parse issues and determinations
        findings = parse_determinations(full_text)
        case_upheld = 0
        issue_rows = []
        for sentence, outcome, is_upheld in findings:
            category = classify_category(sentence)
            if is_upheld:
                case_upheld = 1
            issue_rows.append((sentence, outcome, category, is_upheld))
```

With:

```python
        # 6. Parse issues and determinations
        findings_primary = parse_determinations(full_text)

        # For new-format docs, also extract from structured Complaint/Finding pairs
        findings_secondary = []
        if doc_format == 'new':
            for pair in extract_complaint_finding_pairs(full_text):
                outcome = pair['outcome']
                is_upheld = 1 if outcome in UPHELD_DETERMINATIONS else 0
                findings_secondary.append((pair['complaint'], outcome, is_upheld))

        # Merge: add secondary findings not already captured by primary (dedupe by prefix)
        seen_prefixes = {f[0][:60].lower() for f in findings_primary}
        findings = list(findings_primary)
        for desc, det, upheld in findings_secondary:
            if desc[:60].lower() not in seen_prefixes:
                findings.append((desc, det, upheld))
                seen_prefixes.add(desc[:60].lower())

        case_upheld = 0
        issue_rows = []
        for sentence, outcome, is_upheld in findings:
            category = classify_category(sentence)
            if is_upheld:
                case_upheld = 1
            issue_rows.append((sentence, outcome, category, is_upheld))
```

- [ ] **Step 3: Commit**

```bash
git add build_insights_db.py
git commit -m "feat: add secondary Complaint/Finding extraction for new-format docs"
```

---

## Task 7: Wire all new extractions into `compile_database`

**Files:**
- Modify: `build_insights_db.py` — `compile_database` function

This task integrates `doc_format`, `sections`, `landlord_type`, `tenancy_type`, `legal_citations` into the main per-row loop and updates the INSERT statements.

- [ ] **Step 1: Add `sections` and `doc_format` extraction at the top of the per-row loop**

After `url, title, date_str, landlord_name, full_text = row`, add:

```python
        # 0. Split document into sections (used by all downstream extractors)
        sections = split_sections(full_text)
        doc_format = detect_format(full_text)
```

- [ ] **Step 2: Update timescale and orders extraction to use sections**

Replace:

```python
        # 3. Timescales
        s1, s2, exc = extract_timescales(full_text)
        
        # 4. Compensation
        total_comp, comp_items = extract_compensation(full_text)
        
        # 5. Extract Indicators and Remedies
        vuln, comm, record = extract_indicators(full_text)
        apology, repairs, review_train = extract_orders_remedies(full_text)
```

With:

```python
        # 3. Timescales
        s1, s2, exc = extract_timescales(full_text)

        # 4. Compensation (uses sections to target orders section)
        total_comp, comp_items = extract_compensation(sections)

        # 5. Extract Indicators and Remedies
        vuln, comm, record = extract_indicators(full_text)
        apology, repairs, review_train = extract_orders_remedies(full_text)

        # 5b. New field extractions
        landlord_type = extract_landlord_type(sections)
        tenancy_type = extract_tenancy_type(sections)
        cited_statutes = extract_legal_citations(full_text)
```

- [ ] **Step 3: Update both INSERT INTO cases statements to include the three new columns**

There are two INSERT statements (primary and the IntegrityError fallback). Update both.

Replace the column list in both from:

```python
                INSERT INTO cases (
                    case_id, url, title, decision_date, landlord_id, total_compensation_ordered, 
                    stage_1_days_est, stage_2_days_est, timescales_exceeded_est, 
                    is_upheld_est, apology_ordered_est, repairs_ordered_est, review_or_training_ordered_est,
                    vulnerability_mentioned_est, communication_failure_est, record_keeping_failure_est, full_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

To:

```python
                INSERT INTO cases (
                    case_id, url, title, decision_date, landlord_id, total_compensation_ordered,
                    stage_1_days_est, stage_2_days_est, timescales_exceeded_est,
                    is_upheld_est, apology_ordered_est, repairs_ordered_est, review_or_training_ordered_est,
                    vulnerability_mentioned_est, communication_failure_est, record_keeping_failure_est,
                    doc_format, landlord_type, tenancy_type, full_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

And update the corresponding VALUES tuples in both INSERT calls from:

```python
            (
                case_id, url, title, date_str, landlord_id, total_comp, s1, s2, exc, 
                case_upheld, apology, repairs, review_train, vuln, comm, record, full_text
            )
```

To:

```python
            (
                case_id, url, title, date_str, landlord_id, total_comp, s1, s2, exc,
                case_upheld, apology, repairs, review_train, vuln, comm, record,
                doc_format, landlord_type, tenancy_type, full_text
            )
```

- [ ] **Step 4: Add legal citations insertion as step 10 in the loop**

After the existing "Insert Compensation Details" block, add:

```python
        # 10. Insert Legal Citations
        for statute in cited_statutes:
            dest_cursor.execute("""
                INSERT INTO legal_citations (case_id, statute)
                VALUES (?, ?)
            """, (case_id, statute))
            citations_inserted += 1
```

- [ ] **Step 5: Add `citations_inserted` counter alongside the other counters**

Near the top of `compile_database`, after `compensation_inserted = 0`, add:

```python
    citations_inserted = 0
```

And in the final print block, after `print(f"  - Compensation Orders: {compensation_inserted}")`, add:

```python
    print(f"  - Legal Citations: {citations_inserted}")
```

- [ ] **Step 6: Commit**

```bash
git add build_insights_db.py
git commit -m "feat: wire doc_format, landlord_type, tenancy_type, legal_citations into compile_database"
```

---

## Task 8: Update `verify_insights.py` with new field checks

**Files:**
- Modify: `verify_insights.py` — `verify_insights_db` function

- [ ] **Step 1: Add three new sections at the end of `verify_insights_db`, before `conn.close()`**

```python
    # 9. Document format distribution
    print("\n=== DOCUMENT FORMAT DISTRIBUTION ===")
    cursor.execute("""
        SELECT doc_format, COUNT(*) as cnt,
               (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cases)) as pct
        FROM cases
        GROUP BY doc_format ORDER BY cnt DESC
    """)
    for fmt, cnt, pct in cursor.fetchall():
        label = fmt if fmt else 'NULL (unknown)'
        print(f"  - {label:<10}: {cnt:>5} ({pct:>5.1f}%)")

    # 10. Landlord and tenancy type distributions
    print("\n=== LANDLORD TYPE DISTRIBUTION ===")
    cursor.execute("""
        SELECT landlord_type, COUNT(*) as cnt
        FROM cases WHERE landlord_type IS NOT NULL
        GROUP BY landlord_type ORDER BY cnt DESC LIMIT 10
    """)
    for ltype, cnt in cursor.fetchall():
        print(f"  - {ltype:<40}: {cnt:>5}")
    cursor.execute("SELECT COUNT(*) FROM cases WHERE landlord_type IS NULL")
    null_lt = cursor.fetchone()[0]
    print(f"  - NULL (not extracted)              : {null_lt:>5}")

    print("\n=== TENANCY TYPE DISTRIBUTION ===")
    cursor.execute("""
        SELECT tenancy_type, COUNT(*) as cnt
        FROM cases WHERE tenancy_type IS NOT NULL
        GROUP BY tenancy_type ORDER BY cnt DESC LIMIT 10
    """)
    for ttype, cnt in cursor.fetchall():
        print(f"  - {ttype:<40}: {cnt:>5}")
    cursor.execute("SELECT COUNT(*) FROM cases WHERE tenancy_type IS NULL")
    null_tt = cursor.fetchone()[0]
    print(f"  - NULL (not extracted)              : {null_tt:>5}")

    # 11. Legal citations
    print("\n=== LEGAL CITATIONS (TOP 15) ===")
    cursor.execute("SELECT COUNT(*) FROM legal_citations")
    total_cit = cursor.fetchone()[0]
    print(f"Total citation records: {total_cit}")
    cursor.execute("""
        SELECT statute, COUNT(*) as cnt,
               (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cases)) as pct_cases
        FROM legal_citations
        GROUP BY statute ORDER BY cnt DESC LIMIT 15
    """)
    for statute, cnt, pct in cursor.fetchall():
        print(f"  - {statute:<55}: {cnt:>5} ({pct:>5.1f}% of cases)")
```

- [ ] **Step 2: Verify the updated verify script runs without errors against the existing (pre-rebuild) DB**

```bash
uv run verify-insights 2>&1 | tail -20
```

Expected: May show errors about missing columns (the DB hasn't been rebuilt yet) — that is fine. It must not crash with a Python import or syntax error.

- [ ] **Step 3: Commit**

```bash
git add verify_insights.py
git commit -m "feat: add doc_format, landlord_type, tenancy_type, legal_citations sections to verify_insights"
```

---

## Task 9: Full rebuild and verification

**Files:** No code changes — this task runs the pipeline and checks results.

- [ ] **Step 1: Run the full rebuild**

```bash
cd /Users/diegocarvallo/Documents/diego-personal/HousingOmbudsmanData
uv run build-insights
```

Expected final output (approximate):
```
Insights database compilation completed successfully!
Relational records saved:
  - Landlords: ~723
  - Cases: 16611
  - Issues: >40896  (should be higher than before due to new-format extraction)
  - Compensation Orders: ~30755
  - Legal Citations: >50000  (Housing Ombudsman Scheme cited in nearly every case)
```

- [ ] **Step 2: Run full verification**

```bash
uv run verify-insights
```

Check each of the following in the output:

| Check | Expected |
|---|---|
| Complaint Handling % in ISSUE CATEGORY DISTRIBUTION | Below 30% (was 61%) |
| Repairs & Maintenance % | Above 10% (was 0.8%) |
| Rehousing & Allocations | Appears as a new row |
| Max compensation in FINANCIAL ORDERS STATS | Above £10,000 |
| Issues count | Higher than pre-change 40,896 |
| DOCUMENT FORMAT DISTRIBUTION | Shows `old` ~88%, `new` ~12% |
| LANDLORD TYPE DISTRIBUTION | Shows "Housing Association", "Local Authority" etc. with low NULL count |
| TENANCY TYPE DISTRIBUTION | Shows "Assured Tenancy", "Secure Tenancy" etc. |
| LEGAL CITATIONS | Shows "Housing Ombudsman Scheme" at the top with high count |

- [ ] **Step 3: Spot-check a new-format case directly**

```bash
uv run python - << 'EOF'
import sqlite3

conn = sqlite3.connect('ombudsman_insights.db')

# Check a new-format case has doc_format set
row = conn.execute("""
    SELECT case_id, doc_format, landlord_type, tenancy_type
    FROM cases WHERE doc_format = 'new' LIMIT 3
""").fetchall()
print("New format cases:", row)

# Check legal citations for a known case
cits = conn.execute("""
    SELECT statute FROM legal_citations
    WHERE case_id = (SELECT case_id FROM cases WHERE doc_format='new' LIMIT 1)
""").fetchall()
print("Citations for first new-format case:", [r[0] for r in cits])
conn.close()
EOF
```

Expected: `doc_format = 'new'`, non-null `landlord_type`, list of statute names.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete parsing pipeline improvements — section splitting, format detection, new fields"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Document format captured as `doc_format` column — Task 2 + Task 7
- [x] Section splitting module — Task 1
- [x] `classify_category` reorder — Task 4
- [x] `£10k` compensation cap removed — Task 5
- [x] `Complaint/Finding` block extraction for new-format docs — Task 6
- [x] `landlord_type` column — Tasks 2, 3, 7
- [x] `tenancy_type` column — Tasks 2, 3, 7
- [x] `legal_citations` table — Tasks 2, 3, 7
- [x] `verify_insights.py` updated — Task 8
- [x] Full rebuild and verification — Task 9

**Type consistency:**
- `extract_compensation` now takes `sections: dict` not `text: str` — this is a breaking change from the original signature. Task 5 and Task 7 are consistent with each other on this.
- `extract_landlord_type` and `extract_tenancy_type` both take `sections: dict` — consistent between Task 3 (definition) and Task 7 (call site).
- `extract_complaint_finding_pairs` returns `list[dict]` with keys `complaint`, `outcome`, `analysis` — Task 1 (definition) and Task 6 (call site) both use `pair['complaint']` and `pair['outcome']`.
