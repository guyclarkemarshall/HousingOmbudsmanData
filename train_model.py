#!/usr/bin/env python3
"""
UK Housing Ombudsman - Predictive Model Training & Evaluation
Splits the predictive cases dataset into train/test splits based on date (90 days holdout),
trains machine learning models to predict complaint categories and finding outcomes,
evaluates performance, and serializes the model pipelines.
"""

import os
import sys
import sqlite3
import csv
import datetime
import pickle
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

# Import the existing category classifier
from build_insights_db import classify_category

# Target label spaces
COMPLAINT_CATEGORIES = [
    "Damp & Mould",
    "Pest Control",
    "Leaks & Water Ingress",
    "Anti-Social Behaviour (ASB)",
    "Rent & Service Charges",
    "Estate Management",
    "Repairs & Maintenance",
    "Rehousing & Allocations",
    "Complaint Handling",
    "Other"
]

FINDING_OUTCOMES = [
    "No Maladministration",
    "Service Failure",
    "Maladministration",
    "Severe Maladministration",
    "Reasonable Redress",
    "Outside Jurisdiction"
]

PREDICTIVE_DB = "ombudsman_predictive.db"
INSIGHTS_DB = "ombudsman_insights.db"
TRAIN_CSV = "predictive_db_train.csv"
TEST_CSV = "predictive_db_test.csv"
MODEL_PATH = "predictive_model.pkl"

def fetch_and_split_data():
    """Connects to databases, joins on case_id, splits by date (holdout last 90 days)."""
    if not os.path.exists(PREDICTIVE_DB) or not os.path.exists(INSIGHTS_DB):
        print(f"Error: Required databases '{PREDICTIVE_DB}' or '{INSIGHTS_DB}' not found.")
        sys.exit(1)
        
    print("Connecting to databases and retrieving cases...")
    conn = sqlite3.connect(PREDICTIVE_DB)
    cursor = conn.cursor()
    
    # Cross-database join using ATTACH DATABASE
    cursor.execute(f"ATTACH DATABASE '{INSIGHTS_DB}' AS ins")
    cursor.execute("""
        SELECT pc.case_id, pc.complaint_timeline_text,
               pc.complaint_1, pc.finding_1, pc.complaint_2, pc.finding_2,
               pc.complaint_3, pc.finding_3, pc.complaint_4, pc.finding_4,
               pc.complaint_5, pc.finding_5, pc.complaint_6, pc.finding_6,
               pc.complaint_7, pc.finding_7, pc.complaint_8, pc.finding_8,
               pc.complaint_9, pc.finding_9, pc.complaint_10, pc.finding_10,
               cases.decision_date_iso
        FROM predictive_cases pc
        JOIN ins.cases cases ON pc.case_id = cases.case_id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    print(f"Retrieved {len(rows)} records from database.")
    
    # Parse dates and determine holdout boundary
    valid_dates = [row[-1] for row in rows if row[-1]]
    if not valid_dates:
        print("Error: No valid dates found in the database. Cannot perform time-based split.")
        sys.exit(1)
        
    max_date_str = max(valid_dates)
    max_date = datetime.date.fromisoformat(max_date_str)
    # Subtract 90 days for 3-month holdout
    boundary_date = max_date - datetime.timedelta(days=90)
    boundary_str = boundary_date.isoformat()
    
    print(f"Maximum decision date in dataset: {max_date_str}")
    print(f"Dataset split boundary (past 90 days holdout): {boundary_str}")
    
    train_rows = []
    test_rows = []
    
    for row in rows:
        date_iso = row[-1]
        if date_iso and date_iso >= boundary_str:
            test_rows.append(row)
        else:
            train_rows.append(row)
            
    print(f"Split results: {len(train_rows)} cases in TRAIN, {len(test_rows)} cases in TEST.")
    return train_rows, test_rows

def save_splits_to_db_and_csv(train_rows, test_rows):
    """Saves splits to CSV files and SQLite tables."""
    # 1. Save to CSV
    headers = [
        "Case ID", "Complaint Timeline Text",
        "Complaint 1", "Finding 1", "Complaint 2", "Finding 2",
        "Complaint 3", "Finding 3", "Complaint 4", "Finding 4",
        "Complaint 5", "Finding 5", "Complaint 6", "Finding 6",
        "Complaint 7", "Finding 7", "Complaint 8", "Finding 8",
        "Complaint 9", "Finding 9", "Complaint 10", "Finding 10"
    ]
    
    print(f"Writing train set to {TRAIN_CSV}...")
    with open(TRAIN_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows([row[:-1] for row in train_rows])
        
    print(f"Writing test set to {TEST_CSV}...")
    with open(TEST_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows([row[:-1] for row in test_rows])
        
    # 2. Save to DB tables
    conn = sqlite3.connect(PREDICTIVE_DB)
    create_db_split_table(conn, "predictive_cases_train", train_rows)
    create_db_split_table(conn, "predictive_cases_test", test_rows)
    conn.close()
    print("Successfully wrote splits to database tables.")

def create_db_split_table(conn, table_name, rows):
    """Creates a split table in SQLite and inserts rows."""
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(f"""
        CREATE TABLE {table_name} (
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
    
    # Strip off the decision_date_iso
    insert_data = [row[:-1] for row in rows]
    
    cursor.executemany(f"""
        INSERT OR IGNORE INTO {table_name} (
            case_id, complaint_timeline_text,
            complaint_1, finding_1, complaint_2, finding_2,
            complaint_3, finding_3, complaint_4, finding_4,
            complaint_5, finding_5, complaint_6, finding_6,
            complaint_7, finding_7, complaint_8, finding_8,
            complaint_9, finding_9, complaint_10, finding_10
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_data)
    
    cursor.execute(f"CREATE INDEX idx_{table_name}_case ON {table_name}(case_id)")
    conn.commit()

def prepare_target_matrices(rows):
    """Maps the raw complaints/findings text to multi-label target matrices."""
    category_to_idx = {cat: idx for idx, cat in enumerate(COMPLAINT_CATEGORIES)}
    outcome_to_idx = {out: idx for idx, out in enumerate(FINDING_OUTCOMES)}
    
    # Rows: case_id, timeline_text, complaint_1, finding_1, ...
    y_complaints = np.zeros((len(rows), len(COMPLAINT_CATEGORIES)), dtype=int)
    y_findings = np.zeros((len(rows), len(FINDING_OUTCOMES)), dtype=int)
    
    for i, row in enumerate(rows):
        # Examine up to 10 complaint/finding pairs
        for pair_idx in range(10):
            comp_val = row[2 + pair_idx * 2]
            find_val = row[2 + pair_idx * 2 + 1]
            
            if comp_val:
                cat = classify_category(comp_val)
                if cat in category_to_idx:
                    y_complaints[i, category_to_idx[cat]] = 1
                    
            if find_val:
                find_clean = find_val.strip()
                if find_clean in outcome_to_idx:
                    y_findings[i, outcome_to_idx[find_clean]] = 1
                    
    return y_complaints, y_findings

def train_and_evaluate():
    """Trains TF-IDF + Logistic Regression classifiers and evaluates them on test set."""
    train_rows, test_rows = fetch_and_split_data()
    save_splits_to_db_and_csv(train_rows, test_rows)
    
    # Extract features (timelines)
    X_train = [row[1] for row in train_rows]
    X_test = [row[1] for row in test_rows]
    
    # Extract multi-label target matrices
    y_train_comp, y_train_find = prepare_target_matrices(train_rows)
    y_test_comp, y_test_find = prepare_target_matrices(test_rows)
    
    print("\nTraining Complaint Category Predictor...")
    pipeline_comp = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=10000, stop_words='english')),
        ('clf', MultiOutputClassifier(LogisticRegression(class_weight='balanced', max_iter=1000)))
    ])
    pipeline_comp.fit(X_train, y_train_comp)
    
    print("Training Finding Outcome Predictor...")
    pipeline_find = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=10000, stop_words='english')),
        ('clf', MultiOutputClassifier(LogisticRegression(class_weight='balanced', max_iter=1000)))
    ])
    pipeline_find.fit(X_train, y_train_find)
    
    # Predictions
    print("\nEvaluating on holdout test set...")
    preds_comp = pipeline_comp.predict(X_test)
    preds_find = pipeline_find.predict(X_test)
    
    # Print metrics
    print("\n" + "=" * 60)
    print("=== COMPLAINT CATEGORY CLASSIFICATION PERFORMANCE ===")
    print("=" * 60)
    for idx, name in enumerate(COMPLAINT_CATEGORIES):
        print(f"\nCategory: {name}")
        support = int(y_test_comp[:, idx].sum())
        print(f"Positive Support in Test Set: {support}")
        if support == 0:
            print("Skipping classification report (no positive samples in test set).")
        else:
            print(classification_report(y_test_comp[:, idx], preds_comp[:, idx], target_names=["Absent", "Present"], zero_division=0))
            
    print("\n" + "=" * 60)
    print("=== FINDING OUTCOME CLASSIFICATION PERFORMANCE ===")
    print("=" * 60)
    for idx, name in enumerate(FINDING_OUTCOMES):
        print(f"\nOutcome: {name}")
        support = int(y_test_find[:, idx].sum())
        print(f"Positive Support in Test Set: {support}")
        if support == 0:
            print("Skipping classification report (no positive samples in test set).")
        else:
            print(classification_report(y_test_find[:, idx], preds_find[:, idx], target_names=["Absent", "Present"], zero_division=0))
            
    # Save the models
    print(f"\nSerializing models to {MODEL_PATH}...")
    model_data = {
        "pipeline_comp": pipeline_comp,
        "pipeline_find": pipeline_find,
        "complaint_categories": COMPLAINT_CATEGORIES,
        "finding_outcomes": FINDING_OUTCOMES
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model_data, f)
    print("Model compilation completed successfully!")

if __name__ == "__main__":
    train_and_evaluate()
