#!/usr/bin/env python3
"""
Relational Database Verification Script
Verifies and queries statistical summaries of the compiled ombudsman_insights.db database.
"""

import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "ombudsman_insights_v2.db"

def verify_insights_db():
    print(f"Connecting to database: {DB_NAME}\n")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Row counts
    print("=== RECORD COUNTS ===")
    cursor.execute("SELECT COUNT(*) FROM landlords")
    landlords_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cases")
    cases_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM issues")
    issues_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM compensation_orders")
    comp_count = cursor.fetchone()[0]
    
    print(f"Landlords count          : {landlords_count}")
    print(f"Cases count              : {cases_count}")
    print(f"Issues count             : {issues_count}")
    print(f"Compensation orders count: {comp_count}")
    
    # 2. Issues distributions
    print("\n=== ISSUE CATEGORY DISTRIBUTION ===")
    cursor.execute("""
        SELECT category, COUNT(*) as cnt, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM issues)) as pct
        FROM issues
        GROUP BY category
        ORDER BY cnt DESC
    """)
    for category, cnt, pct in cursor.fetchall():
        print(f"  - {category:<30}: {cnt:>5} ({pct:>5.1f}%)")
        
    print("\n=== DETERMINATION DISTRIBUTION ===")
    cursor.execute("""
        SELECT determination, COUNT(*) as cnt, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM issues)) as pct
        FROM issues
        GROUP BY determination
        ORDER BY cnt DESC
    """)
    for determination, cnt, pct in cursor.fetchall():
        print(f"  - {determination:<25}: {cnt:>5} ({pct:>5.1f}%)")

    # 3. Upheld Rates
    print("\n=== COMPLAINT UPHELD RATES ===")
    cursor.execute("SELECT COUNT(*) FROM cases WHERE is_upheld_est = 1")
    upheld_cases = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM issues WHERE is_upheld_est = 1")
    upheld_issues = cursor.fetchone()[0]
    print(f"Overall Upheld Cases     : {upheld_cases:>5} / {cases_count:<5} ({upheld_cases * 100.0 / cases_count:.1f}%)")
    print(f"Overall Upheld Issues    : {upheld_issues:>5} / {issues_count:<5} ({upheld_issues * 100.0 / issues_count:.1f}%)")
    
    print("\n--- Upheld Rate by Category ---")
    cursor.execute("""
        SELECT category, COUNT(*) as total, SUM(is_upheld_est) as upheld,
               (SUM(is_upheld_est) * 100.0 / COUNT(*)) as rate
        FROM issues
        GROUP BY category
        ORDER BY rate DESC
    """)
    for cat, tot, uph, rate in cursor.fetchall():
        print(f"  - {cat:<30}: {rate:>5.1f}% ({uph}/{tot})")
        
    # 4. Ombudsman Remedies & Orders
    print("\n=== OMBUDSMAN REMEDIES & ORDERS (CASE LEVEL) ===")
    cursor.execute("SELECT SUM(apology_ordered_est) FROM cases")
    apologies = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(repairs_ordered_est) FROM cases")
    repairs = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(review_or_training_ordered_est) FROM cases")
    reviews = cursor.fetchone()[0] or 0
    print(f"  - Apologies Ordered        : {apologies:>5} ({apologies * 100.0 / cases_count:.1f}%)")
    print(f"  - Repairs/Works Ordered    : {repairs:>5} ({repairs * 100.0 / cases_count:.1f}%)")
    print(f"  - Policy/Training Reviews  : {reviews:>5} ({reviews * 100.0 / cases_count:.1f}%)")

    # 5. Operational Heuristics & Context
    print("\n=== OPERATIONAL CONTEXT FLAGS (CASE LEVEL) ===")
    cursor.execute("SELECT SUM(vulnerability_mentioned_est) FROM cases")
    vuln = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(communication_failure_est) FROM cases")
    comm = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(record_keeping_failure_est) FROM cases")
    rec = cursor.fetchone()[0] or 0
    print(f"  - Vulnerability Mentioned  : {vuln:>5} ({vuln * 100.0 / cases_count:.1f}%)")
    print(f"  - Communication Failures   : {comm:>5} ({comm * 100.0 / cases_count:.1f}%)")
    print(f"  - Record Keeping Failures  : {rec:>5} ({rec * 100.0 / cases_count:.1f}%)")

    # 6. Timescale performance metrics
    print("\n=== COMPLAINT TIMESCALE STATS ===")
    cursor.execute("SELECT COUNT(*) FROM cases WHERE stage_1_days_est IS NOT NULL OR stage_2_days_est IS NOT NULL")
    cases_with_timescale = cursor.fetchone()[0]
    print(f"Cases with timescale data: {cases_with_timescale} ({cases_with_timescale * 100.0 / cases_count:.1f}%)")
    
    cursor.execute("SELECT AVG(stage_1_days_est) FROM cases WHERE stage_1_days_est IS NOT NULL AND stage_1_days_est <= 365")
    avg_s1 = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(stage_2_days_est) FROM cases WHERE stage_2_days_est IS NOT NULL AND stage_2_days_est <= 365")
    avg_s2 = cursor.fetchone()[0]
    
    print(f"Average Stage 1 response : {avg_s1:.1f} days (estimates <= 1 year)")
    print(f"Average Stage 2 response : {avg_s2:.1f} days (estimates <= 1 year)")
    
    cursor.execute("SELECT COUNT(*) FROM cases WHERE timescales_exceeded_est = 1")
    exceeded_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE timescales_exceeded_est IS NOT NULL")
    exceeded_known = cursor.fetchone()[0]
    
    if exceeded_known > 0:
        print(f"Exceeded standards rate  : {exceeded_count} out of {exceeded_known} classified ({exceeded_count * 100.0 / exceeded_known:.1f}%)")
        
    # 7. Financial compensation metrics
    print("\n=== FINANCIAL ORDERS STATS ===")
    cursor.execute("SELECT SUM(amount) FROM compensation_orders")
    total_comp = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(DISTINCT case_id) FROM compensation_orders")
    comp_cases = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(total_compensation_ordered) FROM cases WHERE total_compensation_ordered > 0")
    avg_comp_case = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT cases.title, cases.total_compensation_ordered, landlords.name 
        FROM cases 
        JOIN landlords ON cases.landlord_id = landlords.id 
        ORDER BY total_compensation_ordered DESC 
        LIMIT 1
    """)
    max_comp_row = cursor.fetchone()
    
    print(f"Total compensation ordered Across all cases: £{total_comp:,.2f}")
    print(f"Cases with compensation ordered            : {comp_cases} ({comp_cases * 100.0 / cases_count:.1f}%)")
    print(f"Average compensation in cases where ordered: £{avg_comp_case:,.2f}")
    if max_comp_row:
        print(f"Max compensation in a single case          : £{max_comp_row[1]:,.2f}")
        print(f"  - Case    : '{max_comp_row[0]}'")
        print(f"  - Landlord: '{max_comp_row[2]}'")
        
    # 8. Top 5 landlords with highest maladministration count
    print("\n=== TOP 5 LANDLORDS BY MALADMINISTRATION ISSUE COUNT ===")
    cursor.execute("""
        SELECT landlords.name, COUNT(*) as cnt
        FROM issues
        JOIN cases ON issues.case_id = cases.case_id
        JOIN landlords ON cases.landlord_id = landlords.id
        WHERE issues.is_upheld_est = 1
        GROUP BY landlords.name
        ORDER BY cnt DESC
        LIMIT 5
    """)
    for idx, (name, cnt) in enumerate(cursor.fetchall(), 1):
        print(f"  {idx}. {name:<40}: {cnt} issues found failing")
        
    conn.close()

if __name__ == "__main__":
    verify_insights_db()
