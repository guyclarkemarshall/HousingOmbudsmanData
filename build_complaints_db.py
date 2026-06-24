#!/usr/bin/env python3
"""
UK Housing Ombudsman - Complaints & Findings Database Compiler
Extracts structured complaint + finding tables from the decisions text and stores them in a single denormalized SQLite table.
If no tables are found, extracts decision summaries (determinations) from the text.
Also exports the compiled table directly into a CSV file.
"""

import os
import re
import sys
import sqlite3
import csv

# Import helper functions from project files
from section_splitter import (
    split_sections, NORMALIZED_OUTCOMES, parse_case_id, extract_pairs,
    canonical_landlord_name, clean_date_to_iso, LANDLORD_STOCK_SIZES,
)
from build_insights_db import extract_landlord_type, classify_category, parse_determinations

# Set standard output to UTF-8 to prevent console encoding exceptions
sys.stdout.reconfigure(encoding='utf-8')

SRC_DB = "ombudsman_decisions.db"
DEST_DB = "ombudsman_complaints_findings.db"
DEST_CSV = "ombudsman_complaints_findings.csv"

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
            landlord_seq INTEGER,
            landlord_type TEXT,
            decision_date TEXT,
            decision_date_iso TEXT,
            amended_at_review INTEGER,
            category TEXT NOT NULL,
            complaint TEXT NOT NULL,
            finding TEXT NOT NULL,
            extracted_from TEXT NOT NULL,
            stock_size INTEGER,
            decision_id INTEGER NOT NULL
        )
    """)
    
    # Create indices for analytics query optimization
    cursor.execute("CREATE INDEX idx_cf_case ON complaint_findings(case_id)")
    cursor.execute("CREATE INDEX idx_cf_decision ON complaint_findings(decision_id)")
    cursor.execute("CREATE INDEX idx_cf_finding ON complaint_findings(finding)")
    cursor.execute("CREATE INDEX idx_cf_landlord ON complaint_findings(landlord)")
    cursor.execute("CREATE INDEX idx_cf_category ON complaint_findings(category)")
    cursor.execute("CREATE INDEX idx_cf_extracted ON complaint_findings(extracted_from)")
    
    conn.commit()
    conn.close()

def export_to_csv():
    """Queries the database and exports the complaint_findings table to a CSV file."""
    print(f"Exporting records to CSV file: {DEST_CSV}")
    
    conn = sqlite3.connect(DEST_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, case_id, landlord, landlord_seq, landlord_type, decision_date, decision_date_iso, amended_at_review, category, complaint, finding, extracted_from, stock_size, decision_id
        FROM complaint_findings
    """)
    rows = cursor.fetchall()
    
    headers = [
        "Record ID",
        "Case ID",
        "Landlord Name",
        "Landlord Sequence",
        "Landlord Type",
        "Decision Date",
        "Decision Date ISO",
        "Amended at Review",
        "Category",
        "Complaint Description",
        "Finding Outcome",
        "Extracted From",
        "Landlord Stock Size",
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
    
    # Pre-scan landlord types and names to backfill and collapse variants
    print("Pre-scanning decisions to build landlord type mapping...")
    landlord_type_map = {}
    for _, _, _, _, landlord_name, full_text in rows:
        landlord_clean = canonical_landlord_name(landlord_name)
        if landlord_clean not in landlord_type_map or not landlord_type_map[landlord_clean]:
            sections = split_sections(full_text)
            ltype = extract_landlord_type(sections)
            if ltype:
                ltype_clean = ltype.strip()
                if ltype_clean.lower() in ('housing association', 'housing association.'):
                    ltype_clean = 'Housing Association'
                elif ltype_clean.lower() in ('local authority', 'local authority.'):
                    ltype_clean = 'Local Authority'
                elif ltype_clean.lower() in ('local authority / almo or tmo', 'local authority / almo or tmo.'):
                    ltype_clean = 'Local Authority / ALMO or TMO'
                landlord_type_map[landlord_clean] = ltype_clean
                
    # Fallback heuristics for landlords with missing types
    for landlord in set(canonical_landlord_name(r[4]) for r in rows):
        if landlord not in landlord_type_map or not landlord_type_map[landlord]:
            landlord_lower = landlord.lower()
            if any(x in landlord_lower for x in ('council', 'borough of', 'city of', 'corporation of', 'district', 'authority')):
                landlord_type_map[landlord] = 'Local Authority'
            elif any(x in landlord_lower for x in ('association', 'trust', 'homes', 'peabody', 'clarion', 'sanctuary', 'guinness', 'riverside', 'l&q', 'group', 'society')):
                landlord_type_map[landlord] = 'Housing Association'
            else:
                landlord_type_map[landlord] = 'Unknown'

    landlord_cache = {}  # landlord_name -> landlord_seq
    inserted_count = 0
    cases_with_pairs = 0
    
    for idx, row in enumerate(rows, 1):
        doc_id, url, title, decision_date, landlord_name, full_text = row
        case_id = parse_case_id(title, url)
        date_iso, amended = clean_date_to_iso(decision_date)
        
        # Standardize landlord name
        landlord_clean = canonical_landlord_name(landlord_name)
        if landlord_clean not in landlord_cache:
            landlord_cache[landlord_clean] = len(landlord_cache) + 1
        landlord_seq = landlord_cache[landlord_clean]
        stock_size = LANDLORD_STOCK_SIZES.get(landlord_clean)
        
        # Backfill landlord type
        landlord_type = landlord_type_map.get(landlord_clean, "Unknown")
        
        # Try table extraction first
        pairs = extract_pairs(full_text)
        extracted_from = 'table'
        
        # Fallback to parsing text determinations if no table found
        if not pairs:
            dets = parse_determinations(full_text)
            if dets:
                pairs = [(sentence, outcome) for sentence, outcome, _ in dets]
                extracted_from = 'text'
                
        if pairs:
            cases_with_pairs += 1
            deduped_findings = []
            ch_findings = []
            
            outcome_priority = {
                'Severe Maladministration': 6,
                'Maladministration': 5,
                'Service Failure': 4,
                'Reasonable Redress': 3,
                'No Maladministration': 2,
                'Outside Jurisdiction': 1,
            }
            
            for comp, find in pairs:
                category = classify_category(comp)
                find_lower = find.lower()
                normalized_find = NORMALIZED_OUTCOMES.get(find_lower, find)
                
                if category == "Complaint Handling":
                    ch_findings.append((comp, normalized_find, category))
                else:
                    deduped_findings.append((comp, normalized_find, category))
            
            if ch_findings:
                best_ch = max(ch_findings, key=lambda x: outcome_priority.get(x[1], 0))
                deduped_findings.append(best_ch)
                
            for comp, normalized_find, category in deduped_findings:
                dest_cursor.execute("""
                    INSERT INTO complaint_findings (
                        case_id, landlord, landlord_seq, landlord_type, decision_date, decision_date_iso, amended_at_review, category, complaint, finding, extracted_from, stock_size, decision_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (case_id, landlord_clean, landlord_seq, landlord_type, decision_date, date_iso, amended, category, comp, normalized_find, extracted_from, stock_size, doc_id))
                inserted_count += 1
                
        if idx % 2000 == 0 or idx == total_docs:
            dest_conn.commit()
            print(f"Progress: [{idx}/{total_docs}] | Extracted {inserted_count} pairs from {cases_with_pairs} cases.")
            
    src_conn.close()
    dest_conn.close()
    
    print("\nDatabase compilation completed successfully!")
    print(f"Relational records saved:")
    print(f"  - Total Unique Landlords:  {len(landlord_cache)}")
    print(f"  - Total Cases with Pairs:  {cases_with_pairs}")
    print(f"  - Total Pairs Inserted:    {inserted_count}")
    
    # Export to CSV
    export_to_csv()

if __name__ == '__main__':
    build_database()
