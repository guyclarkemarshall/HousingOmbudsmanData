import numpy as np
import pytest
from train_model import prepare_target_matrices, COMPLAINT_CATEGORIES, FINDING_OUTCOMES

def test_prepare_target_matrices():
    # Construct dummy row:
    # (case_id, timeline_text, complaint_1, finding_1, complaint_2, finding_2, ..., date)
    dummy_row = [
        "12345",
        "Chronological events here.",
        "The landlord's response to damp and mould.", # Damp & Mould
        "Maladministration",
        "The landlord's complaint handling response.", # Complaint Handling
        "Service Failure",
        # Empty complaints/findings for the rest
        None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
        "2026-05-26"
    ]
    
    rows = [dummy_row]
    y_comp, y_find = prepare_target_matrices(rows)
    
    # Check shape
    assert y_comp.shape == (1, len(COMPLAINT_CATEGORIES))
    assert y_find.shape == (1, len(FINDING_OUTCOMES))
    
    # Check specific labels
    # Damp & Mould should be 1
    damp_idx = COMPLAINT_CATEGORIES.index("Damp & Mould")
    assert y_comp[0, damp_idx] == 1
    
    # Complaint Handling should be 1
    ch_idx = COMPLAINT_CATEGORIES.index("Complaint Handling")
    assert y_comp[0, ch_idx] == 1
    
    # Repairs & Maintenance should be 0
    rep_idx = COMPLAINT_CATEGORIES.index("Repairs & Maintenance")
    assert y_comp[0, rep_idx] == 0
    
    # Maladministration / Severe Maladministration should be 1 (since dummy_row contains Maladministration)
    mal_idx = FINDING_OUTCOMES.index("Maladministration / Severe Maladministration")
    assert y_find[0, mal_idx] == 1
    
    # Service Failure should be 1
    sf_idx = FINDING_OUTCOMES.index("Service Failure")
    assert y_find[0, sf_idx] == 1
    
    # No Maladministration / Reasonable Redress should be 0
    no_mal_idx = FINDING_OUTCOMES.index("No Maladministration / Reasonable Redress")
    assert y_find[0, no_mal_idx] == 0
