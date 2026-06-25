import os
import sqlite3
import pytest
from build_predictive_db import init_dest_db, extract_timeline_until_referral

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
    assert "url" in columns
    assert "landlord_name" in columns
    assert "complaint_timeline_text" in columns
    assert "complaint_procedure_text" in columns
    
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
