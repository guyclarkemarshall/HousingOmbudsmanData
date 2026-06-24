#!/usr/bin/env python3
"""
UK Housing Ombudsman - Complaints & Findings Database Verification
Queries statistical summaries of the compiled single-table database and validates the exported CSV file.
"""

import os
import sqlite3
import sys
import csv

# Set standard output to UTF-8 to prevent console encoding exceptions
sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "ombudsman_complaints_findings.db"
CSV_NAME = "ombudsman_complaints_findings.csv"

def verify_database():
    if not os.path.exists(DB_NAME):
        print(f"Error: Database {DB_NAME} not found!")
        return
        
    print(f"Connecting to database: {DB_NAME}\n")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Check table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
    print(f"Tables in Database: {tables}")
    
    # 2. Total records
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT case_id), COUNT(DISTINCT landlord) FROM complaint_findings")
    total_records, distinct_cases, distinct_landlords = cursor.fetchone()
    print("\n=== RECORD COUNTS ===")
    print(f"Total Complaint-Finding pairs : {total_records}")
    print(f"Total Unique Case IDs          : {distinct_cases}")
    print(f"Total Unique Landlord Names    : {distinct_landlords}")
    
    if total_records == 0:
        print("No records found in database.")
        conn.close()
        return
        
    # 3. Finding distributions
    print("\n=== FINDING OUTCOME DISTRIBUTION ===")
    cursor.execute("""
        SELECT finding, COUNT(*) as cnt, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM complaint_findings)) as pct
        FROM complaint_findings
        GROUP BY finding
        ORDER BY cnt DESC
    """)
    for finding, cnt, pct in cursor.fetchall():
        print(f"  - {finding:<25}: {cnt:>5} ({pct:>5.1f}%)")
        
    # 4. Category distributions
    print("\n=== COMPLAINT CATEGORY DISTRIBUTION ===")
    cursor.execute("""
        SELECT category, COUNT(*) as cnt, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM complaint_findings)) as pct
        FROM complaint_findings
        GROUP BY category
        ORDER BY cnt DESC
    """)
    for category, cnt, pct in cursor.fetchall():
        print(f"  - {category:<30}: {cnt:>5} ({pct:>5.1f}%)")
        
    # 5. Landlord Type distributions
    print("\n=== LANDLORD TYPE DISTRIBUTION ===")
    cursor.execute("""
        SELECT landlord_type, COUNT(*) as cnt, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM complaint_findings)) as pct
        FROM complaint_findings
        GROUP BY landlord_type
        ORDER BY cnt DESC
    """)
    for ltype, cnt, pct in cursor.fetchall():
        ltype_str = ltype if ltype else "NULL (unknown)"
        print(f"  - {ltype_str:<40}: {cnt:>5} ({pct:>5.1f}%)")
        
    # 6. Sample records
    print("\n=== SAMPLE RECORDS (First 5) ===")
    cursor.execute("""
        SELECT id, case_id, landlord, landlord_type, decision_date, category, complaint, finding, decision_id
        FROM complaint_findings
        LIMIT 5
    """)
    rows = cursor.fetchall()
    for row in rows:
        print("-" * 80)
        print(f"Record ID     : {row[0]}")
        print(f"Case ID       : {row[1]}")
        print(f"Landlord Name : {row[2]}")
        print(f"Landlord Type : {row[3]}")
        print(f"Decision Date : {row[4]}")
        print(f"Category      : {row[5]}")
        print(f"Complaint     : {row[6]}")
        print(f"Finding       : {row[7]}")
        print(f"Decision ID   : {row[8]}")
        
    conn.close()
    
    # 7. Verify CSV file
    print("\n=== CSV EXPORT FILE VALIDATION ===")
    if not os.path.exists(CSV_NAME):
        print(f"Error: Exported CSV file '{CSV_NAME}' not found!")
    else:
        print(f"CSV file '{CSV_NAME}' found.")
        # Count lines in CSV
        with open(CSV_NAME, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            csv_rows = list(reader)
            print(f"Total rows in CSV (including header): {len(csv_rows)}")
            if len(csv_rows) > 1:
                print("Header row      :", csv_rows[0])
                print("First data row  :", csv_rows[1])
                print("Second data row :", csv_rows[2])

if __name__ == '__main__':
    verify_database()
