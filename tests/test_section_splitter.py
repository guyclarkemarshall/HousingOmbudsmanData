"""
Tests for section_splitter.py

TDD: These tests were written BEFORE the implementation.
Uses real document samples from ombudsman_decisions.db.
"""
import sqlite3
import os
import pytest

# Adjust import path so we can find section_splitter at project root
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from section_splitter import detect_format, split_sections, extract_complaint_finding_pairs

# ---------------------------------------------------------------------------
# Real document fixtures sampled from the DB
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ombudsman_decisions.db')


def _load_doc(doc_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT full_text FROM decisions WHERE id = ?', (doc_id,)).fetchone()
    conn.close()
    assert row is not None, f"No document with id={doc_id} in DB"
    return row[0]


# New-format doc: id=50 starts with "Decision\nCase ID"
NEW_FORMAT_DOC = _load_doc(50)

# Old-format doc: id=14251 contains REPORT heading early
OLD_FORMAT_DOC = _load_doc(14251)


# ---------------------------------------------------------------------------
# Synthetic minimal fixtures for edge-case tests
# ---------------------------------------------------------------------------

SYNTHETIC_NEW = (
    "Decision\nCase ID\n999999\nDecision type\nInvestigation\nLandlord\nFoo Housing\n\n"
    "Background\nSome background text.\n"
    "Our investigation\nSome investigation text.\n"
    "Complaint\nDamp and mould issue\nFinding\nMaladministration\nDetailed analysis here.\n"
    "Orders\nPay compensation.\n"
)

SYNTHETIC_OLD = (
    "Home\nDecisions\nSome Housing (12345)\nBack to Top\nREPORT\nCOMPLAINT 12345\n\n"
    "Background\nBackground text.\n"
    "Assessment and findings\nFindings text.\n"
    "Determination (decision)\nDetermination text.\n"
    "Orders\nOrders text.\n"
)

NO_HEADINGS_DOC = (
    "This document has no recognisable section headings. "
    "It is just a block of plain text with no structure at all."
)


# ---------------------------------------------------------------------------
# detect_format tests
# ---------------------------------------------------------------------------

class TestDetectFormat:
    def test_new_format_real_doc(self):
        assert detect_format(NEW_FORMAT_DOC) == 'new'

    def test_old_format_real_doc(self):
        assert detect_format(OLD_FORMAT_DOC) == 'old'

    def test_new_format_synthetic(self):
        assert detect_format(SYNTHETIC_NEW) == 'new'

    def test_old_format_synthetic(self):
        assert detect_format(SYNTHETIC_OLD) == 'old'

    def test_plain_text_defaults_to_old(self):
        # No recognisable new-format marker → falls back to 'old'
        assert detect_format("Just some plain text") == 'old'


# ---------------------------------------------------------------------------
# split_sections tests
# ---------------------------------------------------------------------------

class TestSplitSections:
    def test_old_format_has_background(self):
        secs = split_sections(OLD_FORMAT_DOC)
        assert 'background' in secs

    def test_old_format_real_doc_sections(self):
        secs = split_sections(OLD_FORMAT_DOC)
        # id=14251 has Background, Assessment and findings, Determination, Orders
        assert 'background' in secs
        assert 'assessment_and_findings' in secs

    def test_new_format_has_our_investigation(self):
        secs = split_sections(NEW_FORMAT_DOC)
        assert 'our_investigation' in secs

    def test_new_format_real_doc_sections(self):
        secs = split_sections(NEW_FORMAT_DOC)
        # Should have background and investigation-related sections
        assert 'background' in secs

    def test_new_format_synthetic_sections(self):
        secs = split_sections(SYNTHETIC_NEW)
        assert 'our_investigation' in secs
        assert 'background' in secs

    def test_old_format_synthetic_sections(self):
        secs = split_sections(SYNTHETIC_OLD)
        assert 'background' in secs

    def test_no_headings_returns_full_doc(self):
        secs = split_sections(NO_HEADINGS_DOC)
        assert secs == {'full_doc': NO_HEADINGS_DOC}

    def test_sections_are_non_empty_strings(self):
        secs = split_sections(OLD_FORMAT_DOC)
        for key, val in secs.items():
            assert isinstance(val, str), f"Section '{key}' is not a string"
            assert val.strip() != '', f"Section '{key}' is empty"

    def test_repeated_headings_are_indexed(self):
        # Synthetic doc has Complaint heading (complaint_1)
        secs = split_sections(SYNTHETIC_NEW)
        assert 'complaint_1' in secs


# ---------------------------------------------------------------------------
# extract_complaint_finding_pairs tests
# ---------------------------------------------------------------------------

class TestExtractComplaintFindingPairs:
    def test_old_format_returns_empty_list(self):
        pairs = extract_complaint_finding_pairs(OLD_FORMAT_DOC)
        assert pairs == []

    def test_old_format_synthetic_returns_empty_list(self):
        pairs = extract_complaint_finding_pairs(SYNTHETIC_OLD)
        assert pairs == []

    def test_new_format_real_doc_returns_pairs(self):
        pairs = extract_complaint_finding_pairs(NEW_FORMAT_DOC)
        assert len(pairs) >= 1

    def test_new_format_pair_structure(self):
        pairs = extract_complaint_finding_pairs(NEW_FORMAT_DOC)
        for pair in pairs:
            assert 'complaint' in pair
            assert 'outcome' in pair
            assert 'analysis' in pair
            assert isinstance(pair['complaint'], str)
            assert isinstance(pair['outcome'], str)
            assert isinstance(pair['analysis'], str)

    def test_new_format_outcome_is_normalised(self):
        # outcome values should match normalised labels, not raw lowercase
        pairs = extract_complaint_finding_pairs(NEW_FORMAT_DOC)
        valid_outcomes = {
            'Severe Maladministration', 'No Maladministration', 'Maladministration',
            'Service Failure', 'Reasonable Redress', 'Outside Jurisdiction',
        }
        for pair in pairs:
            assert pair['outcome'] in valid_outcomes, (
                f"Unexpected outcome value: {pair['outcome']!r}"
            )

    def test_synthetic_new_format_single_pair(self):
        pairs = extract_complaint_finding_pairs(SYNTHETIC_NEW)
        assert len(pairs) == 1
        assert pairs[0]['complaint'] == 'Damp and mould issue'
        assert pairs[0]['outcome'] == 'Maladministration'
        assert pairs[0]['analysis'] == 'Detailed analysis here.'
