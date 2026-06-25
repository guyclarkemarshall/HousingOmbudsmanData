"""
Tests for extract_landlord_type, extract_tenancy_type, extract_legal_citations
in build_insights_db.py

TDD: Tests written BEFORE the implementation functions are added.
Uses synthetic section dicts and a real doc from ombudsman_decisions.db.
"""
import os
import sys
import sqlite3
import pytest

# Adjust import path so project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_insights_db import extract_landlord_type, extract_tenancy_type, extract_legal_citations
from section_splitter import split_sections

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ombudsman_decisions.db')
db_exists = os.path.exists(DB_PATH)

requires_db = pytest.mark.skipif(not db_exists, reason="ombudsman_decisions.db not found")


def _load_doc(doc_id: int) -> str:
    if not db_exists:
        return ""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT full_text FROM decisions WHERE id = ?', (doc_id,)).fetchone()
    conn.close()
    assert row is not None, f"No document with id={doc_id} in DB"
    return row[0]


# ---------------------------------------------------------------------------
# extract_landlord_type
# ---------------------------------------------------------------------------

class TestExtractLandlordType:

    def test_returns_value_from_preamble(self):
        """Returns the value that follows 'Landlord type\n' in the preamble key."""
        sections = {
            'preamble': 'Decision\nCase ID\n202300001\nLandlord type\nHousing Association\nOccupancy\nAssured Tenancy'
        }
        result = extract_landlord_type(sections)
        assert result == 'Housing Association'

    def test_falls_back_to_full_doc(self):
        """Falls back to full_doc key when preamble key is absent (old-format docs)."""
        sections = {
            'full_doc': 'Decision\nCase ID\n202300002\nLandlord type\nLocal Authority / ALMO or TMO\nOccupancy\nSecure Tenancy\n' + 'x' * 600
        }
        result = extract_landlord_type(sections)
        assert result == 'Local Authority / ALMO or TMO'

    def test_full_doc_fallback_only_searches_first_500_chars(self):
        """full_doc fallback only looks in the first 500 characters — avoids false positives deep in body text."""
        # Put the Landlord type header beyond 500 chars
        sections = {
            'full_doc': 'a' * 501 + '\nLandlord type\nHousing Association\n'
        }
        result = extract_landlord_type(sections)
        assert result is None

    def test_returns_none_when_absent(self):
        """Returns None when neither preamble nor full_doc contains 'Landlord type' header."""
        sections = {'preamble': 'No relevant header here', 'full_doc': 'Also nothing useful.'}
        result = extract_landlord_type(sections)
        assert result is None

    def test_returns_none_when_sections_empty(self):
        """Returns None gracefully on empty sections dict."""
        result = extract_landlord_type({})
        assert result is None

    def test_strips_whitespace(self):
        """Strips trailing/leading whitespace from extracted value."""
        sections = {'preamble': 'Landlord type\n  Private Registered Provider  \n'}
        result = extract_landlord_type(sections)
        assert result == 'Private Registered Provider'


# ---------------------------------------------------------------------------
# extract_tenancy_type
# ---------------------------------------------------------------------------

class TestExtractTenancyType:

    def test_returns_value_from_preamble(self):
        """Returns the value following 'Occupancy\n' in the preamble."""
        sections = {
            'preamble': 'Decision\nCase ID\n202300003\nLandlord type\nHousing Association\nOccupancy\nAssured Tenancy\nDate\n1 January 2025'
        }
        result = extract_tenancy_type(sections)
        assert result == 'Assured Tenancy'

    def test_falls_back_to_full_doc(self):
        """Falls back to full_doc when preamble absent."""
        sections = {
            'full_doc': 'Occupancy\nSecure Tenancy\nDate\n2 February 2025\n' + 'x' * 600
        }
        result = extract_tenancy_type(sections)
        assert result == 'Secure Tenancy'

    def test_returns_none_when_absent(self):
        """Returns None when Occupancy header not present."""
        sections = {'preamble': 'Some text with no occupancy header'}
        result = extract_tenancy_type(sections)
        assert result is None

    def test_returns_none_when_sections_empty(self):
        """Returns None gracefully on empty sections dict."""
        result = extract_tenancy_type({})
        assert result is None

    def test_strips_whitespace(self):
        """Strips whitespace from extracted value."""
        sections = {'preamble': 'Occupancy\n  Licence  \n'}
        result = extract_tenancy_type(sections)
        assert result == 'Licence'


# ---------------------------------------------------------------------------
# extract_legal_citations
# ---------------------------------------------------------------------------

class TestExtractLegalCitations:

    def test_returns_matching_statutes(self):
        """Returns statute names when they appear in the text."""
        text = "The landlord must comply with the Housing Act 1996 and the Equality Act 2010."
        result = extract_legal_citations(text)
        assert 'Housing Act 1996' in result
        assert 'Equality Act 2010' in result

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        text = "This document references the HOUSING ACT 1996 and awaab's law."
        result = extract_legal_citations(text)
        assert 'Housing Act 1996' in result
        assert "Awaab's Law" in result

    def test_returns_empty_list_when_no_statutes(self):
        """Returns an empty list when no known statutes are present."""
        text = "This is a generic text with no legal citations whatsoever."
        result = extract_legal_citations(text)
        assert result == []

    def test_deduplicates_same_statute(self):
        """Each statute name appears at most once in the result even if cited multiple times."""
        text = (
            "The Housing Act 1996 sets out the framework. "
            "Under the Housing Act 1996 the landlord must..."
        )
        result = extract_legal_citations(text)
        assert result.count('Housing Act 1996') == 1

    def test_hhsrs_abbreviation_detected(self):
        """HHSRS abbreviation is detected as a legal citation."""
        text = "The HHSRS assessment found category 1 hazards."
        result = extract_legal_citations(text)
        assert 'HHSRS' in result

    def test_returns_list_type(self):
        """Always returns a list (not None or some other type)."""
        result = extract_legal_citations("")
        assert isinstance(result, list)

    def test_multiple_statutes_detected(self):
        """Detects multiple distinct statutes in the same document."""
        text = (
            "The Landlord and Tenant Act 1985 requires repairs. "
            "The Decent Homes Standard was not met. "
            "The Care Act 2014 applies to vulnerable residents."
        )
        result = extract_legal_citations(text)
        assert 'Landlord and Tenant Act 1985' in result
        assert 'Decent Homes Standard' in result
        assert 'Care Act 2014' in result


# ---------------------------------------------------------------------------
# Smoke test: real old-format document (id=28943)
# ---------------------------------------------------------------------------

@requires_db
class TestSmokeRealDoc:

    def test_smoke_old_format_doc(self):
        """
        Smoke test against a real old-format document (id=28943).
        Old-format docs lack 'Landlord type'/'Occupancy' metadata, so those
        extractors return None. Legal citations should find Housing Act 1996
        which appears in every old-format doc's boilerplate.
        """
        full_text = _load_doc(28943)
        sections = split_sections(full_text)

        # Old-format docs don't embed the landlord/tenancy metadata in the header
        # so both should be None
        landlord_type = extract_landlord_type(sections)
        tenancy_type = extract_tenancy_type(sections)
        assert landlord_type is None
        assert tenancy_type is None

        # Every old-format doc contains boilerplate referencing Housing Act 1996
        citations = extract_legal_citations(full_text)
        assert isinstance(citations, list)
        assert 'Housing Act 1996' in citations

    def test_smoke_new_format_doc(self):
        """
        Smoke test against a real new-format document (id=1).
        Should return landlord_type and tenancy_type strings.
        """
        full_text = _load_doc(1)
        sections = split_sections(full_text)

        landlord_type = extract_landlord_type(sections)
        tenancy_type = extract_tenancy_type(sections)

        assert landlord_type is not None, "New-format doc should have a landlord type"
        assert tenancy_type is not None, "New-format doc should have a tenancy type"
        assert isinstance(landlord_type, str)
        assert isinstance(tenancy_type, str)
        assert len(landlord_type) > 0
        assert len(tenancy_type) > 0
