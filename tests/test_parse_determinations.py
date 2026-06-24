"""
Unit tests for parse_determinations in build_insights_db.py.
"""
import os
import sys
import pytest

# Adjust path to find build_insights_db
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_insights_db import parse_determinations


def test_standard_determination_block():
    """Tests standard extraction from a Determination block."""
    text = (
        "Determination\n"
        "In respect of the complaint about damp and mould, there was severe maladministration. "
        "In respect of the complaint handling, there was a service failure."
    )
    results = parse_determinations(text)
    assert len(results) == 2
    
    # Check damp and mould
    desc1, outcome1, upheld1 = results[0]
    assert "severe maladministration" in desc1.lower()
    assert outcome1 == "Severe Maladministration"
    assert upheld1 == 1
    
    # Check complaint handling
    desc2, outcome2, upheld2 = results[1]
    assert "service failure" in desc2.lower()
    assert outcome2 == "Service Failure"
    assert upheld2 == 1


def test_abbreviation_lookbehind_sentence_splitting():
    """Tests that common abbreviations do not cause incorrect sentence splitting."""
    text = (
        "Our decision\n"
        "The landlord's response to reports of leaks by Mr. Smith was maladministration. "
        "The inspection of No. 24 St. Jude's Road on 14 Jan. 2025 was a service failure."
    )
    results = parse_determinations(text)
    assert len(results) == 2
    
    # Mr. Smith check
    desc1, outcome1, upheld1 = results[0]
    assert "Mr. Smith" in desc1
    assert outcome1 == "Maladministration"
    
    # No. and St. and Jan. check
    desc2, outcome2, upheld2 = results[1]
    assert "No. 24 St. Jude's" in desc2
    assert outcome2 == "Service Failure"


def test_outcome_priority_and_upheld_status():
    """Tests that outcomes are matched in correct order of specificity and upheld status is set."""
    # Test severe maladministration priority over maladministration
    text = (
        "We found:\n"
        "The landlord was guilty of severe maladministration in its record keeping."
    )
    results = parse_determinations(text)
    assert len(results) == 1
    assert results[0][1] == "Severe Maladministration"
    assert results[0][2] == 1

    # Test outside jurisdiction (not upheld)
    text = (
        "Determination\n"
        "The complaint about the level of rent is outside the jurisdiction of the Ombudsman."
    )
    results = parse_determinations(text)
    assert len(results) == 1
    assert results[0][1] == "Outside Jurisdiction"
    assert results[0][2] == 0
