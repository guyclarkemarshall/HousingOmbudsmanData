"""
Unit tests for extract_orders_remedies in build_insights_db.py.
"""
import os
import sys
import pytest

# Adjust path to find build_insights_db
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_insights_db import extract_orders_remedies


def test_extract_orders_remedies_apology():
    """Tests detection of apology order in the orders section."""
    sections = {
        'orders': "The landlord shall write a letter of apology to the resident.",
        'background': "The resident requested an apology."
    }
    apology, repairs, review = extract_orders_remedies(sections)
    assert apology == 1
    assert repairs == 0
    assert review == 0


def test_extract_orders_remedies_repairs():
    """Tests detection of repair order in the orders section."""
    sections = {
        'putting_things_right': "The landlord must inspect the windows and complete repairs.",
        'background': "The landlord completed works."
    }
    apology, repairs, review = extract_orders_remedies(sections)
    assert apology == 0
    assert repairs == 1
    assert review == 0


def test_extract_orders_remedies_policy_review():
    """Tests detection of staff training/policy reviews in the orders section."""
    sections = {
        'orders_and_recommendations': "The landlord shall conduct a policy review and staff training.",
        'background': "The staff had training last year."
    }
    apology, repairs, review = extract_orders_remedies(sections)
    assert apology == 0
    assert repairs == 0
    assert review == 1


def test_extract_orders_remedies_false_positive_avoidance():
    """Tests that keyword matches in background narratives are ignored if orders section exists."""
    sections = {
        'background': "The resident wanted an apology and repairs on their boiler.",
        'orders': "The landlord shall pay compensation."
    }
    apology, repairs, review = extract_orders_remedies(sections)
    assert apology == 0
    assert repairs == 0
    assert review == 0


def test_extract_orders_remedies_fallback_to_full_doc():
    """Tests that full_doc is used as a fallback if no specific orders section is present."""
    sections = {
        'full_doc': "The landlord is ordered to apologise."
    }
    apology, repairs, review = extract_orders_remedies(sections)
    assert apology == 1
    assert repairs == 0
    assert review == 0
