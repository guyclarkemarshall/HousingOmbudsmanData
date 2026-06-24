"""
Unit tests for extract_pairs in section_splitter.py.
"""
import os
import sys
import pytest

# Adjust path to find section_splitter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from section_splitter import extract_pairs


def test_extract_pairs_standard():
    """Tests standard Complaint/Finding pair extraction."""
    text = (
        "Complaint\n"
        "The landlord's response to reports of water leaks.\n"
        "Finding\n"
        "Maladministration\n"
    )
    pairs = extract_pairs(text)
    assert len(pairs) == 1
    assert pairs[0] == ("The landlord's response to reports of water leaks.", "Maladministration")


def test_extract_pairs_multiple():
    """Tests extraction of multiple pairs."""
    text = (
        "Complaint\n"
        "First complaint description.\n"
        "Finding\n"
        "Service Failure\n"
        "Complaint\n"
        "Second complaint description.\n"
        "Finding\n"
        "No Maladministration\n"
    )
    pairs = extract_pairs(text)
    assert len(pairs) == 2
    assert pairs[0] == ("First complaint description.", "Service Failure")
    assert pairs[1] == ("Second complaint description.", "No Maladministration")


def test_extract_pairs_spacing_and_trailing_periods():
    """Tests resilience to leading/trailing spaces, blank lines, and trailing periods on outcomes."""
    text = (
        "\n"
        "  Complaint  \n"
        "\n"
        "  The landlord's handling of damp and mould.  \n"
        "\n"
        "  Finding  \n"
        "  Severe Maladministration.  \n"
    )
    pairs = extract_pairs(text)
    assert len(pairs) == 1
    assert pairs[0] == ("The landlord's handling of damp and mould.", "Severe Maladministration")


def test_extract_pairs_invalid_finding_outcome():
    """Tests that outcomes not present in NORMALIZED_OUTCOMES are ignored to prevent false positives."""
    text = (
        "Complaint\n"
        "Description of complaint.\n"
        "Finding\n"
        "This is not a valid outcome statement\n"
    )
    pairs = extract_pairs(text)
    assert len(pairs) == 0


def test_extract_pairs_consecutive_complaints():
    """Tests that consecutive Complaint headers without a Finding are handled cleanly."""
    text = (
        "Complaint\n"
        "First complaint without finding.\n"
        "Complaint\n"
        "Second complaint with finding.\n"
        "Finding\n"
        "Reasonable Redress\n"
    )
    pairs = extract_pairs(text)
    assert len(pairs) == 1
    assert pairs[0] == ("Second complaint with finding.", "Reasonable Redress")
