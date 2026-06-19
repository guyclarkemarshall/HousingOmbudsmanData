#!/usr/bin/env python3
"""
Simple script to verify the contents of the SQLite decisions database.
"""

import sqlite3
import os

DB_NAME = "ombudsman_decisions.db"

def verify_database():
    if not os.path.exists(DB_NAME):
        print(f"Error: Database {DB_NAME} not found!")
        return
        
    print(f"Connecting to database: {DB_NAME}")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check table schema
    cursor.execute("PRAGMA table_info(decisions)")
    columns = cursor.fetchall()
    print("\n=== Table Schema (decisions) ===")
    for col in columns:
        print(f"Column ID: {col[0]} | Name: {col[1]} | Type: {col[2]} | NotNull: {col[3]} | Default: {col[4]} | PK: {col[5]}")
        
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM decisions")
    count = cursor.fetchone()[0]
    print(f"\nTotal records in decisions table: {count}")
    
    if count == 0:
        print("No records found in database.")
        conn.close()
        return
        
    # Query sample rows
    cursor.execute("""
        SELECT id, url, title, decision_date, landlord, length(full_text)
        FROM decisions
        LIMIT 5
    """)
    rows = cursor.fetchall()
    
    print("\n=== Sample Records (First 5) ===")
    for row in rows:
        print("-" * 80)
        print(f"ID: {row[0]}")
        print(f"URL: {row[1]}")
        print(f"Title: {row[2]}")
        print(f"Date: {row[3]}")
        print(f"Landlord: {row[4]}")
        print(f"Full Text Length: {row[5]} characters")
        
        # Get a snippet of the full text
        cursor.execute("SELECT full_text FROM decisions WHERE id = ?", (row[0],))
        full_text = cursor.fetchone()[0]
        snippet = "\n".join(full_text.splitlines()[:5])
        print(f"Snippet:\n{snippet}\n...")
        
    # Check for anomalies
    print("\n=== Anomalies Check ===")
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE title IS NULL OR title = ''")
    null_titles = cursor.fetchone()[0]
    print(f"Records with missing title: {null_titles}")
    
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE decision_date IS NULL OR decision_date = ''")
    null_dates = cursor.fetchone()[0]
    print(f"Records with missing date: {null_dates}")
    
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE landlord IS NULL OR landlord = ''")
    null_landlords = cursor.fetchone()[0]
    print(f"Records with missing landlord: {null_landlords}")
    
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE full_text IS NULL OR length(full_text) < 100")
    short_texts = cursor.fetchone()[0]
    print(f"Records with very short or missing full text (< 100 chars): {short_texts}")
    
    conn.close()

if __name__ == "__main__":
    verify_database()
