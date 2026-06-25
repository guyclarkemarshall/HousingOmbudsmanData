#!/usr/bin/env python3
"""
Simple script to verify the contents of the SQLite predictive database.
"""

import sqlite3
import os
import sys

DB_NAME = "ombudsman_predictive.db"

def verify_database():
    if not os.path.exists(DB_NAME):
        print(f"Error: Database {DB_NAME} not found!")
        return False
        
    print(f"Connecting to database: {DB_NAME}")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check table schema
    cursor.execute("PRAGMA table_info(predictive_cases)")
    columns = cursor.fetchall()
    print("\n=== Table Schema (predictive_cases) ===")
    for col in columns:
        print(f"Column ID: {col[0]} | Name: {col[1]} | Type: {col[2]} | NotNull: {col[3]} | Default: {col[4]} | PK: {col[5]}")
        
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM predictive_cases")
    count = cursor.fetchone()[0]
    print(f"\nTotal records in predictive_cases table: {count}")
    
    if count == 0:
        print("No records found in database.")
        conn.close()
        return False
        
    # Get count of records with timeline text
    cursor.execute("SELECT COUNT(*) FROM predictive_cases WHERE complaint_timeline_text IS NOT NULL AND length(complaint_timeline_text) > 0")
    timeline_count = cursor.fetchone()[0]
    print(f"Records with non-empty timeline text: {timeline_count} ({timeline_count / count * 100:.1f}%)")

    # Get count of records with procedure text
    cursor.execute("SELECT COUNT(*) FROM predictive_cases WHERE complaint_procedure_text IS NOT NULL AND length(complaint_procedure_text) > 0")
    procedure_count = cursor.fetchone()[0]
    print(f"Records with non-empty procedure text: {procedure_count} ({procedure_count / count * 100:.1f}%)")
    
    # Get count of cases with at least one complaint finding pair
    cursor.execute("SELECT COUNT(*) FROM predictive_cases WHERE complaint_1 IS NOT NULL")
    pairs_count = cursor.fetchone()[0]
    print(f"Cases with at least one parsed complaint-finding pair: {pairs_count} ({pairs_count / count * 100:.1f}%)")

    # Query sample rows
    cursor.execute("""
        SELECT case_id, landlord_name, length(complaint_timeline_text), complaint_1, finding_1
        FROM predictive_cases
        WHERE complaint_1 IS NOT NULL
        LIMIT 3
    """)
    rows = cursor.fetchall()
    
    print("\n=== Sample Records ===")
    for row in rows:
        print("-" * 80)
        print(f"Case ID: {row[0]}")
        print(f"Landlord: {row[1]}")
        print(f"Timeline Length: {row[2]} characters")
        print(f"Complaint 1: {row[3][:120]}...")
        print(f"Finding 1: {row[4]}")
        
    conn.close()
    return True

def main():
    success = verify_database()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
