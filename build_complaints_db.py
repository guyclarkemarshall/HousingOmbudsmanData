#!/usr/bin/env python3
"""
UK Housing Ombudsman - Complaints & Findings Database Compiler
Extracts structured complaint + finding tables from the decisions text and stores them in a single denormalized SQLite table.
Also exports the compiled table directly into a CSV file.
"""

import os
import re
import sys
import sqlite3
import csv

# Import helper functions from project files
from section_splitter import split_sections
from build_insights_db import extract_landlord_type, classify_category

# Set standard output to UTF-8 to prevent console encoding exceptions
sys.stdout.reconfigure(encoding='utf-8')

SRC_DB = "ombudsman_decisions.db"
DEST_DB = "ombudsman_complaints_findings.db"
DEST_CSV = "ombudsman_complaints_findings.csv"

# Valid finding outcomes and their normalized casings
NORMALIZED_OUTCOMES = {
    'no maladministration': 'No Maladministration',
    'service failure': 'Service Failure',
    'maladministration': 'Maladministration',
    'severe maladministration': 'Severe Maladministration',
    'reasonable redress': 'Reasonable Redress',
    'outside jurisdiction': 'Outside Jurisdiction',
    'choose an item.': 'Choose an item.'
}

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

def extract_pairs(text):
    """Parses text line-by-line to extract complaint and finding pairs."""
    if not text:
        return []
        
    text = text.replace('\r\n', '\n')
    lines = text.split('\n')
    
    pairs = []
    i = 0
    n = len(lines)
    
    while i < n:
        line = lines[i].strip()
        if line.lower() == 'complaint':
            complaint_lines = []
            j = i + 1
            found_finding = False
            
            while j < n:
                next_line = lines[j].strip()
                if next_line.lower() == 'complaint':
                    # Hit another Complaint header without finding a Finding block first
                    break
                if next_line.lower() == 'finding':
                    found_finding = True
                    break
                complaint_lines.append(next_line)
                j += 1
            
            if found_finding and j + 1 < n:
                outcome = lines[j+1].strip()
                outcome_clean = outcome.rstrip('.').strip()
                outcome_lower = outcome_clean.lower()
                if outcome_lower in NORMALIZED_OUTCOMES:
                    complaint_desc = " ".join(" ".join(complaint_lines).split()).strip()
                    normalized_outcome = NORMALIZED_OUTCOMES[outcome_lower]
                    pairs.append((complaint_desc, normalized_outcome))
                    i = j + 2
                    continue
        i += 1
        
    return pairs

def init_dest_db(db_path):
    """Initializes the single-table database schema."""
    if os.path.exists(db_path):
        print(f"Removing existing database file: {db_path}")
        os.remove(db_path)
        
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Single Denormalized Table
    cursor.execute("""
        CREATE TABLE complaint_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            landlord TEXT,
            landlord_type TEXT,
            decision_date TEXT,
            category TEXT NOT NULL,
            complaint TEXT NOT NULL,
            finding TEXT NOT NULL,
            decision_id INTEGER NOT NULL
        )
    """)
    
    # Create indices for analytics query optimization
    cursor.execute("CREATE INDEX idx_cf_case ON complaint_findings(case_id)")
    cursor.execute("CREATE INDEX idx_cf_decision ON complaint_findings(decision_id)")
    cursor.execute("CREATE INDEX idx_cf_finding ON complaint_findings(finding)")
    cursor.execute("CREATE INDEX idx_cf_landlord ON complaint_findings(landlord)")
    cursor.execute("CREATE INDEX idx_cf_category ON complaint_findings(category)")
    
    conn.commit()
    conn.close()

def export_to_csv():
    """Queries the database and exports the complaint_findings table to a CSV file."""
    print(f"Exporting records to CSV file: {DEST_CSV}")
    
    conn = sqlite3.connect(DEST_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, case_id, landlord, landlord_type, decision_date, category, complaint, finding, decision_id
        FROM complaint_findings
    """)
    rows = cursor.fetchall()
    
    headers = [
        "Record ID",
        "Case ID",
        "Landlord Name",
        "Landlord Type",
        "Decision Date",
        "Category",
        "Complaint Description",
        "Finding Outcome",
        "Source Decision ID"
    ]
    
    # Use 'utf-8-sig' to ensure Excel on Windows correctly detects UTF-8 encoding
    with open(DEST_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    conn.close()
    print(f"Successfully exported {len(rows)} records to {DEST_CSV}")

def build_database():
    if not os.path.exists(SRC_DB):
        print(f"Error: Source database '{SRC_DB}' not found!")
        sys.exit(1)
        
    init_dest_db(DEST_DB)
    
    src_conn = sqlite3.connect(SRC_DB)
    src_cursor = src_conn.cursor()
    
    dest_conn = sqlite3.connect(DEST_DB)
    dest_cursor = dest_conn.cursor()
    
    src_cursor.execute("SELECT id, url, title, decision_date, landlord, full_text FROM decisions")
    rows = src_cursor.fetchall()
    total_docs = len(rows)
    print(f"Loaded {total_docs} cases from source database. Extracting pairs and metadata...")
    
    inserted_count = 0
    cases_with_pairs = 0
    
    for idx, row in enumerate(rows, 1):
        doc_id, url, title, decision_date, landlord_name, full_text = row
        case_id = parse_case_id(title, url)
        
        pairs = extract_pairs(full_text)
        if pairs:
            cases_with_pairs += 1
            
            # Standardize landlord
            landlord_clean = landlord_name.strip() if landlord_name else "Unknown Landlord"
            
            # Extract landlord type by splitting sections
            sections = split_sections(full_text)
            landlord_type = extract_landlord_type(sections)
            
            for comp, find in pairs:
                # Classify the category of the complaint
                category = classify_category(comp)
                
                dest_cursor.execute("""
                    INSERT INTO complaint_findings (
                        case_id, landlord, landlord_type, decision_date, category, complaint, finding, decision_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (case_id, landlord_clean, landlord_type, decision_date, category, comp, find, doc_id))
                inserted_count += 1
                
        if idx % 2000 == 0 or idx == total_docs:
            dest_conn.commit()
            print(f"Progress: [{idx}/{total_docs}] | Extracted {inserted_count} pairs from {cases_with_pairs} cases.")
            
    src_conn.close()
    dest_conn.close()
    
    print("\nDatabase compilation completed successfully!")
    print(f"Relational records saved:")
    print(f"  - Total Cases with Pairs:  {cases_with_pairs}")
    print(f"  - Total Pairs Inserted:    {inserted_count}")
    
    # Export to CSV
    export_to_csv()

if __name__ == '__main__':
    build_database()
