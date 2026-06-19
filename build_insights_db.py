#!/usr/bin/env python3
"""
UK Housing Ombudsman Decisions - Insights Database Compiler
Parses unstructured decisions text into a structured relational SQLite database.
"""

import os
import re
import sys
import sqlite3

# Config
SRC_DB = "ombudsman_decisions.db"
DEST_DB = "ombudsman_insights.db"

# Set standard output to UTF-8 to prevent console encoding exceptions
sys.stdout.reconfigure(encoding='utf-8')

# Output patterns in order of specificity (No maladministration must precede maladministration)
OUTCOME_PATTERNS = [
    (r'\b(severe maladministration)\b', 'Severe Maladministration'),
    (r'\b(no maladministration)\b', 'No Maladministration'),
    (r'\b(maladministration)\b', 'Maladministration'),
    (r'\b(service failure)\b', 'Service Failure'),
    (r'\b(reasonable redress|satisfactory offer of redress|redress)\b', 'Reasonable Redress'),
    (r'\b(outside jurisdiction|outside the jurisdiction)\b', 'Outside Jurisdiction')
]

def init_dest_db(db_path):
    """Initializes the relational destination database schema."""
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Initializing relational insights database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # 1. Landlords Lookup Table
    cursor.execute("""
        CREATE TABLE landlords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # 2. Cases Table
    cursor.execute("""
        CREATE TABLE cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            url TEXT,
            title TEXT,
            decision_date TEXT,
            landlord_id INTEGER,
            total_compensation_ordered REAL DEFAULT 0.0,
            stage_1_days_est INTEGER,
            stage_2_days_est INTEGER,
            timescales_exceeded_est INTEGER,
            full_text TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlords(id)
        )
    """)
    
    # 3. Issues Table
    cursor.execute("""
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            description TEXT NOT NULL,
            determination TEXT NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        )
    """)
    
    # 4. Compensation Orders Table
    cursor.execute("""
        CREATE TABLE compensation_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        )
    """)
    
    # Indices for speed and analytical query optimization
    cursor.execute("CREATE INDEX idx_cases_landlord ON cases(landlord_id)")
    cursor.execute("CREATE INDEX idx_issues_case ON issues(case_id)")
    cursor.execute("CREATE INDEX idx_issues_category ON issues(category)")
    cursor.execute("CREATE INDEX idx_issues_determination ON issues(determination)")
    cursor.execute("CREATE INDEX idx_comp_case ON compensation_orders(case_id)")
    
    conn.commit()
    conn.close()

def parse_case_id(title, url):
    """Extracts a unique case ID from the title or URL."""
    # Try looking in title (usually e.g. "Housing Trust (202347433)")
    match = re.search(r'\((\d{7,9})\)', title)
    if match:
        return match.group(1)
        
    # Fallback to URL (usually ends with landlord-name-caseid/)
    match = re.search(r'-(\d{7,9})/?$', url)
    if match:
        return match.group(1)
        
    # Generates a pseudo-id if none found
    import hashlib
    return "pseudo_" + hashlib.md5(url.encode()).hexdigest()[:8]

def parse_determinations(text):
    """Heuristic extraction of determination outcomes and their descriptions."""
    clean_text = ' '.join(text.split())
    
    # Try finding standard determination block
    det_match = re.search(
        r'(Our decision \(determination\)|Our decision|We found:|We found the landlord responsible for:)(.*?)(Summary of reasons|Orders and recommendations|Orders|Putting things right|$)', 
        clean_text, 
        re.IGNORECASE
    )
    if not det_match:
        # Fallback: scan the end of the text
        pos = clean_text.lower().rfind("our decision")
        if pos != -1:
            section_text = clean_text[pos:pos+2500]
        else:
            section_text = clean_text[-3000:]
    else:
        section_text = det_match.group(2).strip()
        
    sentences = re.split(r'\.\s*(?=[A-Z])', section_text)
    results = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        found_outcome = None
        for pattern, label in OUTCOME_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                found_outcome = label
                break
                
        if found_outcome:
            # Clean up introductory prefixes like "We found: " or "a)"
            cleaned_sentence = re.sub(r'^(We found:|We have found:|\s*[a-z0-9\)\.\-\s]+)+', '', sentence, flags=re.IGNORECASE).strip()
            if cleaned_sentence:
                results.append((cleaned_sentence, found_outcome))
            
    return results

def classify_category(desc):
    """Classifies dispute descriptions into discrete standard categories."""
    desc_lower = desc.lower()
    
    if re.search(r'\b(damp|mould|condensation)\b', desc_lower):
        return "Damp & Mould"
    elif re.search(r'\b(leak|water|flood|burst|ingress|piping)\b', desc_lower):
        return "Leaks & Water Ingress"
    elif re.search(r'\b(noise|antisocial|asb|anti-social|harassment|nuisance)\b', desc_lower):
        return "Anti-Social Behaviour (ASB)"
    elif re.search(r'\b(complaint|handling|escalation|stages?|response)\b', desc_lower):
        return "Complaint Handling"
    elif re.search(r'\b(repair|maintenance|window|roof|boiler|heating|hot water|door|lift|gutter|structure)\b', desc_lower):
        return "Repairs & Maintenance"
    else:
        return "Other"

def extract_timescales(text):
    """Parses response timescales and standard compliance metrics from text."""
    clean_text = ' '.join(text.split())
    
    stage1_days = None
    stage2_days = None
    exceeded = None
    
    s1_match = re.search(r'stage 1\b.{1,150}?\b(\d+)\b\s*(working|calendar)?\s*days', clean_text, re.I)
    if s1_match:
        stage1_days = int(s1_match.group(1))
        
    s2_match = re.search(r'stage 2\b.{1,150}?\b(\d+)\b\s*(working|calendar)?\s*days', clean_text, re.I)
    if s2_match:
        stage2_days = int(s2_match.group(1))
        
    if re.search(r'\b(exceeded|outside|delayed|delay of|fail to meet)\b.{1,100}?\b(timescale|policy|standard|guideline|limit)\b', clean_text, re.I):
        exceeded = 1
    elif re.search(r'\b(within|met|complied with|adhered to)\b.{1,100}?\b(timescale|policy|standard)\b', clean_text, re.I):
        exceeded = 0
        
    return stage1_days, stage2_days, exceeded

def extract_compensation(text):
    """Extracts ordered compensation values and descriptions from the Orders section."""
    clean_text = ' '.join(text.split())
    
    ord_match = re.search(r'\b(Orders|Putting things right)\b(.*?)(Recommendations|Discretion|$)', clean_text, re.IGNORECASE)
    if not ord_match:
        pos = clean_text.lower().rfind("orders")
        if pos != -1:
            section_text = clean_text[pos:]
        else:
            section_text = clean_text[-3000:]
    else:
        section_text = ord_match.group(2).strip()
        
    sentences = re.split(r'\.\s*(?=[A-Z])', section_text)
    total_amount = 0.0
    items = []
    
    for sentence in sentences:
        matches = re.findall(r'£([0-9,]+)', sentence)
        for m in matches:
            val_str = m.replace(',', '')
            try:
                val = float(val_str)
                # Bounds check to avoid mapping claims or rents
                if 20.0 <= val <= 10000.0:
                    total_amount += val
                    items.append((val, sentence.strip()[:250]))
            except ValueError:
                pass
                
    return total_amount, items

def compile_database():
    """Reads cases, parses insights, and saves relational structured entries."""
    if not os.path.exists(SRC_DB):
        print(f"Error: Source database '{SRC_DB}' not found!")
        sys.exit(1)
        
    init_dest_db(DEST_DB)
    
    # Establish connections
    src_conn = sqlite3.connect(SRC_DB)
    src_cursor = src_conn.cursor()
    
    dest_conn = sqlite3.connect(DEST_DB)
    dest_cursor = dest_conn.cursor()
    dest_cursor.execute("PRAGMA foreign_keys = ON")
    
    # Fetch all source records
    src_cursor.execute("SELECT url, title, decision_date, landlord, full_text FROM decisions")
    rows = src_cursor.fetchall()
    total_cases = len(rows)
    print(f"Loaded {total_cases} raw cases. Commencing parsing...")
    
    landlord_cache = {}  # name -> id
    
    cases_inserted = 0
    issues_inserted = 0
    compensation_inserted = 0
    
    for idx, row in enumerate(rows, 1):
        url, title, date_str, landlord_name, full_text = row
        
        # 1. Clean and standardize landlord
        landlord_clean = landlord_name.strip() if landlord_name else "Unknown Landlord"
        if landlord_clean not in landlord_cache:
            dest_cursor.execute("INSERT OR IGNORE INTO landlords (name) VALUES (?)", (landlord_clean,))
            # Fetch id
            dest_cursor.execute("SELECT id FROM landlords WHERE name = ?", (landlord_clean,))
            landlord_cache[landlord_clean] = dest_cursor.fetchone()[0]
            
        landlord_id = landlord_cache[landlord_clean]
        
        # 2. Extract Case ID & clean Date
        case_id = parse_case_id(title, url)
        
        # 3. Timescales
        s1, s2, exc = extract_timescales(full_text)
        
        # 4. Compensation
        total_comp, comp_items = extract_compensation(full_text)
        
        # 5. Insert Case
        try:
            dest_cursor.execute("""
                INSERT INTO cases (case_id, url, title, decision_date, landlord_id, total_compensation_ordered, stage_1_days_est, stage_2_days_est, timescales_exceeded_est, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id, url, title, date_str, landlord_id, total_comp, s1, s2, exc, full_text
            ))
            cases_inserted += 1
        except sqlite3.IntegrityError:
            # Handle duplicate case IDs gracefully (e.g. if scraping overlapping ranges)
            # Append hash suffix to keep unique
            import hashlib
            case_id = case_id + "_" + hashlib.md5(url.encode()).hexdigest()[:4]
            dest_cursor.execute("""
                INSERT INTO cases (case_id, url, title, decision_date, landlord_id, total_compensation_ordered, stage_1_days_est, stage_2_days_est, timescales_exceeded_est, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id, url, title, date_str, landlord_id, total_comp, s1, s2, exc, full_text
            ))
            cases_inserted += 1
            
        # 6. Parse and Insert Issues (Determinations)
        findings = parse_determinations(full_text)
        for sentence, outcome in findings:
            category = classify_category(sentence)
            dest_cursor.execute("""
                INSERT INTO issues (case_id, description, determination, category)
                VALUES (?, ?, ?, ?)
            """, (case_id, sentence, outcome, category))
            issues_inserted += 1
            
        # 7. Insert Compensation Details
        for amount, desc in comp_items:
            dest_cursor.execute("""
                INSERT INTO compensation_orders (case_id, amount, description)
                VALUES (?, ?, ?)
            """, (case_id, amount, desc))
            compensation_inserted += 1
            
        # Periodically commit and log progress
        if idx % 1000 == 0 or idx == total_cases:
            dest_conn.commit()
            print(f"Progress: [{idx}/{total_cases}] | Stored: {cases_inserted} cases, {issues_inserted} issues, {compensation_inserted} compensation items.")
            
    # Clean up and final report
    src_conn.close()
    dest_conn.close()
    
    print("\nInsights database compilation completed successfully!")
    print(f"Relational records saved:")
    print(f"  - Landlords: {len(landlord_cache)}")
    print(f"  - Cases: {cases_inserted}")
    print(f"  - Issues: {issues_inserted}")
    print(f"  - Compensation Orders: {compensation_inserted}")

if __name__ == "__main__":
    compile_database()
