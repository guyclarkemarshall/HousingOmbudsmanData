#!/usr/bin/env python3
"""
UK Housing Ombudsman - Predictive Modeling Dataset Compiler
Compiles case timelines and internal landlord complaint handling text alongside 
parsed complaint/finding pairs into a flat SQLite table and CSV for machine learning.
"""

import os
import re
import sys
import sqlite3
import csv

# Import helper functions from project files
from section_splitter import (
    split_sections, NORMALIZED_OUTCOMES, parse_case_id, extract_pairs,
    canonical_landlord_name, clean_date_to_iso, detect_format,
)
from build_insights_db import parse_determinations

# Set standard output to UTF-8 to prevent console encoding exceptions
sys.stdout.reconfigure(encoding='utf-8')

SRC_DB = "ombudsman_decisions.db"
DEST_DB = "ombudsman_predictive.db"
DEST_CSV = "ombudsman_predictive.csv"

def extract_timeline_until_referral(full_text, sections):
    fmt = detect_format(full_text)
    referral_re = re.compile(
        r'\b(referred|complained|brought|asked|sought|contacted|approached)\b.*\b(ombudsman|this\s+service|our\s+service|us\b)\b'
        r'|the\s+ombudsman\s+wrote\s+to|this\s+service\s+wrote\s+to'
        r'|Referral to the Ombudsman|Referral to this Service|Referral to our Service', 
        re.IGNORECASE
    )
    
    if fmt == 'new':
        start_pat = re.compile(r'^\s*(Our investigation|The complaint procedure)\s*$|^\s*(Date\s*\n\s*What happened)\s*$', re.MULTILINE | re.IGNORECASE)
        start_match = start_pat.search(full_text)
        
        if not start_match:
            # Fallback to sections if regex fails
            timeline_src = sections.get('background', '')
        else:
            start_pos = start_match.start()
            end_pat = re.compile(r'^\s*(Referral to the Ombudsman|Referral to this Service|Referral to our Service)\s*$', re.MULTILINE | re.IGNORECASE)
            end_match = end_pat.search(full_text, start_match.end())
            
            next_heading_pat = re.compile(
                r'^\s*(What we found|What we found and why|Complaint|Finding|Our decision|Summary of reasons|Putting things right|Orders|Recommendations)\s*$',
                re.MULTILINE | re.IGNORECASE
            )
            
            if not end_match:
                next_match = next_heading_pat.search(full_text, start_match.end())
                if next_match:
                    timeline_src = full_text[start_pos:next_match.start()]
                else:
                    timeline_src = full_text[start_pos:start_pos+8000]
            else:
                next_match = next_heading_pat.search(full_text, end_match.end())
                if next_match:
                    timeline_src = full_text[start_pos:next_match.start()]
                else:
                    timeline_src = full_text[start_pos:end_match.end() + 2000]
                    
        sentences = re.split(r'(?<=[.!?])\s+', ' '.join(timeline_src.split()))
        truncated_sentences = []
        for s in sentences:
            truncated_sentences.append(s)
            if referral_re.search(s):
                break
        return ' '.join(truncated_sentences).strip()
    else:
        # Old format: Background or Summary of events
        timeline_src = sections.get('background', '') or sections.get('background_and_summary_of_events', '') or sections.get('summary_of_events', '')
        if not timeline_src:
            start_pat = re.compile(r'^\s*(Background|Summary of events)\s*$', re.MULTILINE | re.IGNORECASE)
            start_match = start_pat.search(full_text)
            if not start_match:
                timeline_src = full_text[:5000]
            else:
                start_pos = start_match.end()
                end_pat = re.compile(r'^\s*(Assessment and findings|Scope|Complaint handling|Determination|Orders|Recommendations)\s*$', re.MULTILINE | re.IGNORECASE)
                end_match = end_pat.search(full_text, start_pos)
                if end_match:
                    timeline_src = full_text[start_pos:end_match.start()]
                else:
                    timeline_src = full_text[start_pos:start_pos+12000]
                    
        sentences = re.split(r'(?<=[.!?])\s+', ' '.join(timeline_src.split()))
        truncated_sentences = []
        for s in sentences:
            truncated_sentences.append(s)
            if referral_re.search(s):
                break
        return ' '.join(truncated_sentences).strip()


def init_dest_db(db_path):
    """Initializes the database schema with a flat predictive cases table."""
    if os.path.exists(db_path):
        print(f"Removing existing database file: {db_path}")
        os.remove(db_path)
        
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the predictive cases table
    cursor.execute("""
        CREATE TABLE predictive_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            complaint_timeline_text TEXT,
            complaint_1 TEXT,
            finding_1 TEXT,
            complaint_2 TEXT,
            finding_2 TEXT,
            complaint_3 TEXT,
            finding_3 TEXT,
            complaint_4 TEXT,
            finding_4 TEXT,
            complaint_5 TEXT,
            finding_5 TEXT,
            complaint_6 TEXT,
            finding_6 TEXT,
            complaint_7 TEXT,
            finding_7 TEXT,
            complaint_8 TEXT,
            finding_8 TEXT,
            complaint_9 TEXT,
            finding_9 TEXT,
            complaint_10 TEXT,
            finding_10 TEXT
        )
    """)
    
    # Create index for analytics optimization
    cursor.execute("CREATE INDEX idx_pc_case ON predictive_cases(case_id)")
    
    conn.commit()
    conn.close()

def export_to_csv():
    """Queries the database and exports the predictive_cases table to a CSV file."""
    print(f"Exporting records to CSV file: {DEST_CSV}")
    
    conn = sqlite3.connect(DEST_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT case_id, complaint_timeline_text,
               complaint_1, finding_1, complaint_2, finding_2,
               complaint_3, finding_3, complaint_4, finding_4,
               complaint_5, finding_5, complaint_6, finding_6,
               complaint_7, finding_7, complaint_8, finding_8,
               complaint_9, finding_9, complaint_10, finding_10
        FROM predictive_cases
    """)
    rows = cursor.fetchall()
    
    headers = [
        "Case ID", "Complaint Timeline Text",
        "Complaint 1", "Finding 1", "Complaint 2", "Finding 2",
        "Complaint 3", "Finding 3", "Complaint 4", "Finding 4",
        "Complaint 5", "Finding 5", "Complaint 6", "Finding 6",
        "Complaint 7", "Finding 7", "Complaint 8", "Finding 8",
        "Complaint 9", "Finding 9", "Complaint 10", "Finding 10"
    ]
    
    # Use 'utf-8-sig' to ensure Excel on Windows correctly detects UTF-8 encoding
    with open(DEST_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    conn.close()
    print(f"Successfully exported {len(rows)} records to {DEST_CSV}")

def extract_complaints_from_complaint_section(text):
    if not text:
        return []
    text_clean = text.replace('\r\n', '\n').strip()
    lines = text_clean.split('\n')
    complaints = []
    
    intro_patterns = [
        re.compile(r'complaint\s+is\s+about', re.I),
        re.compile(r'complaints\s+are\s+about', re.I),
        re.compile(r'resident\s+complained\s+about', re.I),
        re.compile(r'representative\s+complained\s+about', re.I),
    ]
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if any(pat.search(line_clean) for pat in intro_patterns) and len(line_clean) < 80:
            continue
        line_clean = re.sub(r'^(?:[•\-\*\u2022\u2023\u2043\u25e6\u25c9\u25cb\u25cf\u25d8\u25d9]|\d+[\)\.]|[a-zA-Z][\)\.])\s*', '', line_clean).strip()
        if line_clean and len(line_clean) > 5:
            complaints.append(' '.join(line_clean.split()))
            
    if len(complaints) <= 1:
        raw_text = ' '.join(text_clean.split())
        matches = re.split(r'\b(?:\d+|[a-g])[\)\.]\s+', raw_text)
        if len(matches) > 1:
            potential_complaints = []
            for part in matches[1:]:
                part_clean = part.strip()
                if part_clean and len(part_clean) > 5:
                    potential_complaints.append(part_clean)
            if potential_complaints:
                complaints = potential_complaints
                
    return complaints

def main():
    if not os.path.exists(SRC_DB):
        print(f"Error: Source database '{SRC_DB}' not found!")
        sys.exit(1)
        
    init_dest_db(DEST_DB)
    
    src_conn = sqlite3.connect(SRC_DB)
    src_cursor = src_conn.cursor()
    
    dest_conn = sqlite3.connect(DEST_DB)
    dest_cursor = dest_conn.cursor()
    
    src_cursor.execute("SELECT url, title, decision_date, landlord, full_text FROM decisions")
    rows = src_cursor.fetchall()
    total_docs = len(rows)
    print(f"Loaded {total_docs} cases from source database. Extracting timeline and pairs...")
    
    inserted_count = 0
    
    for idx, row in enumerate(rows, 1):
        url, title, decision_date, landlord_name, full_text = row
        case_id = parse_case_id(title, url)
        
        # Split document into sections
        sections = split_sections(full_text)
        doc_format = detect_format(full_text)
        
        # Extract Timeline Text
        timeline_text = extract_timeline_until_referral(full_text, sections)
            
        # Extract complaint-finding pairs
        if doc_format == 'new':
            pairs = extract_pairs(full_text)
            
            # Fallback to parsing text determinations if no table found
            if not pairs:
                dets = parse_determinations(full_text)
                if dets:
                    pairs = [(sentence, outcome) for sentence, outcome, _ in dets]
        else:
            # Old format: Extract complaints from top and findings from bottom
            comp_start_pat = re.compile(r'(?:^|\n)\s*the\s+compl\s*a\s*i\s*n\s*t\b', re.IGNORECASE)
            comp_end_pat = re.compile(r'(?:^|\n)\s*(?:back\s*g\s*r\s*o\s*u\s*n\s*d|summary\s+of\s+events)\b', re.IGNORECASE)
            
            start_match = comp_start_pat.search(full_text)
            complaint_sec = ""
            if start_match:
                end_match = comp_end_pat.search(full_text, start_match.end())
                if end_match:
                    complaint_sec = full_text[start_match.end():end_match.start()]
                else:
                    complaint_sec = full_text[start_match.end():start_match.end() + 2000]
                    
            complaints = extract_complaints_from_complaint_section(complaint_sec)
            dets = parse_determinations(full_text)
            findings = [outcome for _, outcome, _ in dets]
            
            pairs = []
            for i in range(max(len(complaints), len(findings))):
                comp = complaints[i] if i < len(complaints) else ""
                find = findings[i] if i < len(findings) else ""
                pairs.append((comp, find))
        
        # Initialize complaint/finding columns
        cf_cols = [None] * 20 # 10 pairs (complaint, finding)
        
        if pairs:
            for pair_idx, (comp, find) in enumerate(pairs[:10]):
                find_lower = find.lower()
                normalized_find = NORMALIZED_OUTCOMES.get(find_lower, find)
                cf_cols[pair_idx * 2] = comp.strip()
                cf_cols[pair_idx * 2 + 1] = normalized_find.strip()
                
        # Insert record into database
        dest_cursor.execute("""
            INSERT OR IGNORE INTO predictive_cases (
                case_id,
                complaint_timeline_text,
                complaint_1, finding_1, complaint_2, finding_2,
                complaint_3, finding_3, complaint_4, finding_4,
                complaint_5, finding_5, complaint_6, finding_6,
                complaint_7, finding_7, complaint_8, finding_8,
                complaint_9, finding_9, complaint_10, finding_10
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            timeline_text,
            cf_cols[0], cf_cols[1], cf_cols[2], cf_cols[3],
            cf_cols[4], cf_cols[5], cf_cols[6], cf_cols[7],
            cf_cols[8], cf_cols[9], cf_cols[10], cf_cols[11],
            cf_cols[12], cf_cols[13], cf_cols[14], cf_cols[15],
            cf_cols[16], cf_cols[17], cf_cols[18], cf_cols[19]
        ))
        inserted_count += 1
        
        if idx % 2000 == 0 or idx == total_docs:
            dest_conn.commit()
            print(f"Progress: [{idx}/{total_docs}] | Processed {inserted_count} cases.")
            
    src_conn.close()
    dest_conn.close()
    
    print("\nPredictive dataset compilation completed successfully!")
    
    # Export to CSV
    export_to_csv()

if __name__ == '__main__':
    main()
