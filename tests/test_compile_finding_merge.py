"""
Tests for Task 6: secondary Complaint/Finding block extraction merge logic.

These are unit tests of the merge logic used in compile_database step 6.
They do not require the full pipeline — they test the deduplication and
is_upheld logic in isolation.
"""
import sys
import os
import pytest

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_insights_db import UPHELD_DETERMINATIONS
from section_splitter import detect_format, extract_complaint_finding_pairs


# ---------------------------------------------------------------------------
# Helper: reproduce the merge logic from compile_database step 6
# ---------------------------------------------------------------------------

def merge_findings(findings_primary, doc_format, full_text):
    """Mirrors the step-6 merge logic from compile_database."""
    findings_secondary = []
    if doc_format == 'new':
        for pair in extract_complaint_finding_pairs(full_text):
            outcome = pair['outcome']
            is_upheld = 1 if outcome in UPHELD_DETERMINATIONS else 0
            findings_secondary.append((pair['complaint'], outcome, is_upheld))

    seen_prefixes = {f[0][:60].lower() for f in findings_primary}
    findings = list(findings_primary)
    for desc, det, upheld in findings_secondary:
        if desc[:60].lower() not in seen_prefixes:
            findings.append((desc, det, upheld))
            seen_prefixes.add(desc[:60].lower())

    return findings


# ---------------------------------------------------------------------------
# Minimal new-format document stub
# ---------------------------------------------------------------------------

NEW_FORMAT_DOC = """\
Decision
Case ID 202500001
Landlord Some Housing Trust
Landlord type Social landlord
Occupancy Secure tenant

Our investigation

Complaint
The landlord failed to repair the roof within a reasonable time.
Finding
Maladministration
The landlord took 18 months to repair a leak that should have been fixed in weeks.

Complaint
The landlord did not respond to the resident's stage 1 complaint.
Finding
Service failure
The landlord failed to acknowledge the complaint within the required 5 days.

Orders and recommendations
"""


OLD_FORMAT_DOC = """\
REPORT

Background

Some background text.

Assessment and findings

The landlord was found to have caused service failure in relation to repairs.

Orders

Pay £200 compensation.
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocFormatDetection:
    def test_new_format_detected(self):
        assert detect_format(NEW_FORMAT_DOC) == 'new'

    def test_old_format_detected(self):
        assert detect_format(OLD_FORMAT_DOC) == 'old'


class TestIsUpheldFromDetermination:
    """is_upheld must follow UPHELD_DETERMINATIONS set."""

    @pytest.mark.parametrize("outcome,expected", [
        ('Maladministration', 1),
        ('Severe Maladministration', 1),
        ('Service Failure', 1),
        ('No Maladministration', 0),
        ('Reasonable Redress', 0),
        ('Outside Jurisdiction', 0),
    ])
    def test_is_upheld_classification(self, outcome, expected):
        is_upheld = 1 if outcome in UPHELD_DETERMINATIONS else 0
        assert is_upheld == expected, f"Expected {expected} for '{outcome}'"


class TestMergeLogic:

    def test_old_format_secondary_is_empty(self):
        """For old-format docs no secondary findings are extracted."""
        primary = [("The landlord failed to handle the complaint.", "Service Failure", 1)]
        merged = merge_findings(primary, doc_format='old', full_text=OLD_FORMAT_DOC)
        assert merged == primary

    def test_new_format_secondary_added_when_not_in_primary(self):
        """New secondary findings not in primary get appended."""
        primary = []  # nothing from parse_determinations
        merged = merge_findings(primary, doc_format='new', full_text=NEW_FORMAT_DOC)

        # Should have 2 findings from the Complaint/Finding pairs
        assert len(merged) == 2

        descriptions = [m[0] for m in merged]
        assert any('roof' in d.lower() for d in descriptions)
        assert any('complaint' in d.lower() for d in descriptions)

    def test_new_format_secondary_not_duplicated_when_prefix_matches_primary(self):
        """A secondary finding whose first-60-char prefix matches a primary is skipped."""
        complaint_text = "The landlord failed to repair the roof within a reasonable time."
        # Primary already has this description
        primary = [(complaint_text, "Maladministration", 1)]
        merged = merge_findings(primary, doc_format='new', full_text=NEW_FORMAT_DOC)

        # The roof complaint is deduped; only the stage-1 complaint is added
        descriptions = [m[0] for m in merged]
        assert descriptions.count(complaint_text) == 1  # no duplicate
        assert len(merged) == 2  # primary (1) + one new secondary

    def test_primary_findings_preserved_in_full_merge(self):
        """Primary findings are always included regardless of secondary."""
        primary = [("Some entirely different prior finding.", "No Maladministration", 0)]
        merged = merge_findings(primary, doc_format='new', full_text=NEW_FORMAT_DOC)

        # Primary preserved + 2 new secondary
        assert len(merged) == 3
        assert merged[0] == primary[0]

    def test_dedup_uses_60_char_prefix(self):
        """Deduplication ignores text beyond the first 60 characters."""
        # Build a description whose first 60 chars match the new-format complaint
        complaint_text = "The landlord failed to repair the roof within a reasonable t"  # exactly 60 chars
        assert len(complaint_text) == 60

        # Add as a primary with a slightly different suffix
        primary = [(complaint_text + "me (additional context).", "Maladministration", 1)]
        merged = merge_findings(primary, doc_format='new', full_text=NEW_FORMAT_DOC)

        # The new-format Complaint 1 starts with same 60-char prefix → deduplicated
        roof_entries = [m for m in merged if 'roof' in m[0].lower()]
        assert len(roof_entries) == 1

    def test_empty_primary_and_old_format_returns_empty(self):
        """Old format + empty primary → empty result."""
        merged = merge_findings([], doc_format='old', full_text=OLD_FORMAT_DOC)
        assert merged == []

    def test_secondary_outcomes_correctly_mapped(self):
        """Outcomes from new-format pairs carry correct is_upheld values."""
        merged = merge_findings([], doc_format='new', full_text=NEW_FORMAT_DOC)
        outcome_map = {m[0]: (m[1], m[2]) for m in merged}

        # First complaint → Maladministration → is_upheld=1
        roof_key = next(k for k in outcome_map if 'roof' in k.lower())
        assert outcome_map[roof_key] == ('Maladministration', 1)

        # Second complaint → Service Failure → is_upheld=1
        complaint_key = next(k for k in outcome_map if 'complaint' in k.lower())
        assert outcome_map[complaint_key] == ('Service Failure', 1)
