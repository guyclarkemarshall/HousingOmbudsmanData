import os
import sqlite3
import pytest
from build_predictive_db import init_dest_db, extract_timeline_until_referral, extract_complaints_from_complaint_section

TEST_DB = "test_predictive.db"

@pytest.fixture
def clean_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_init_dest_db(clean_db):
    init_dest_db(clean_db)
    assert os.path.exists(clean_db)
    
    conn = sqlite3.connect(clean_db)
    cursor = conn.cursor()
    
    # Verify table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictive_cases'")
    assert cursor.fetchone() is not None
    
    # Verify schema columns
    cursor.execute("PRAGMA table_info(predictive_cases)")
    columns = {col[1]: col[2] for col in cursor.fetchall()}
    
    assert "case_id" in columns
    assert "complaint_timeline_text" in columns
    assert "url" not in columns
    assert "landlord_name" not in columns
    assert "complaint_procedure_text" not in columns
    assert "title" not in columns
    assert "decision_date" not in columns
    assert "decision_date_iso" not in columns
    
    # Verify sequential complaint-finding pairs columns
    for i in range(1, 11):
        assert f"complaint_{i}" in columns
        assert f"finding_{i}" in columns
        
    conn.close()

def test_extract_timeline_until_referral_new_format():
    full_text = (
        "Decision\nCase ID\n12345\n"
        "Background\nSome introductory info here.\n"
        "Our investigation\nThe complaint procedure\n"
        "Date\nWhat happened\n"
        "1 January 2026\nThe tenant complained to the landlord about the leak.\n"
        "10 January 2026\nThe landlord inspected the leak.\n"
        "Referral to the Ombudsman\n"
        "The resident was unhappy with the landlord's final response and referred the complaint to us on 15 January.\n"
        "They wanted additional compensation.\n"
        "What we found\nWe found maladministration."
    )
    sections = {
        "background": "Some introductory info here.",
        "our_investigation": (
            "The complaint procedure\nDate\nWhat happened\n"
            "1 January 2026\nThe tenant complained to the landlord about the leak.\n"
            "10 January 2026\nThe landlord inspected the leak.\n"
            "Referral to the Ombudsman\n"
            "The resident was unhappy with the landlord's final response and referred the complaint to us on 15 January.\n"
            "They wanted additional compensation."
        )
    }
    
    timeline = extract_timeline_until_referral(full_text, sections)
    
    # Timeline should include the start heading and the chronological events,
    # plus the first sentence under Referral to the Ombudsman, but not the second sentence.
    assert "Our investigation" in timeline
    assert "1 January 2026" in timeline
    assert "10 January 2026" in timeline
    assert "referred the complaint to us" in timeline
    assert "They wanted additional compensation" not in timeline
    assert "What we found" not in timeline

def test_extract_timeline_until_referral_old_format():
    full_text = (
        "REPORT\n"
        "Background\n"
        "The resident complained to the landlord on 1 January 2026. The landlord failed to resolve the issue. "
        "The resident brought the complaint to the Ombudsman on 20 January 2026. The Ombudsman contacted the landlord.\n"
        "Assessment and findings\n"
        "The landlord's policy states..."
    )
    sections = {
        "background": (
            "The resident complained to the landlord on 1 January 2026. The landlord failed to resolve the issue. "
            "The resident brought the complaint to the Ombudsman on 20 January 2026. The Ombudsman contacted the landlord."
        )
    }
    
    timeline = extract_timeline_until_referral(full_text, sections)
    
    # Should stop at the sentence where the resident brought the complaint to the Ombudsman
    assert "The resident complained to the landlord on 1 January 2026." in timeline
    assert "The landlord failed to resolve the issue." in timeline
    assert "The resident brought the complaint to the Ombudsman on 20 January 2026." in timeline
    assert "The Ombudsman contacted the landlord" not in timeline

def test_extract_complaints_from_complaint_section():
    # Test text with typical intro and list markers
    text = (
        "The complaint is about:\n"
        "1. The landlord's response to the resident's reports of a leak.\n"
        "2. The landlord's complaint handling.\n"
        "3. The landlord's record keeping."
    )
    complaints = extract_complaints_from_complaint_section(text)
    assert len(complaints) == 3
    assert complaints[0] == "The landlord's response to the resident's reports of a leak."
    assert complaints[1] == "The landlord's complaint handling."
    assert complaints[2] == "The landlord's record keeping."

    # Test text with bullet points
    text_bullet = (
        "The complaints are about:\n"
        "• First complaint item.\n"
        "- Second complaint item."
    )
    complaints_bullet = extract_complaints_from_complaint_section(text_bullet)
    assert len(complaints_bullet) == 2
    assert complaints_bullet[0] == "First complaint item."
    assert complaints_bullet[1] == "Second complaint item."

def test_pairing_old_format_no_leakage():
    # Test zipping complaints from top and determinations from bottom
    complaints = ["Complaint item A", "Complaint item B"]
    findings = ["Service Failure", "No Maladministration"]
    
    pairs = []
    for i in range(max(len(complaints), len(findings))):
        comp = complaints[i] if i < len(complaints) else ""
        find = findings[i] if i < len(findings) else ""
        pairs.append((comp, find))
        
    assert len(pairs) == 2
    assert pairs[0] == ("Complaint item A", "Service Failure")
    assert pairs[1] == ("Complaint item B", "No Maladministration")

