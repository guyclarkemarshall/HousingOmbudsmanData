"""
Tests for helper functions in section_splitter.py
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from section_splitter import canonical_landlord_name, clean_date_to_iso

class TestCanonicalLandlordName:
    @pytest.mark.parametrize("input_name, expected", [
        ("Lambeth Council", "London Borough of Lambeth"),
        ("lambeth", "London Borough of Lambeth"),
        ("L&Q Housing", "London & Quadrant Housing Trust (L&Q)"),
        ("Clarion Housing", "Clarion Housing Association"),
        ("Peabody", "Peabody Trust"),
        ("Some random landlord Ltd.", "Some Random Landlord"),
        ("A2 Dominion", "A2Dominion Housing Group"),
        ("", "Unknown Landlord"),
        (None, "Unknown Landlord"),
    ])
    def test_canonical_landlord_name(self, input_name, expected):
        assert canonical_landlord_name(input_name) == expected


class TestCleanDateToIso:
    @pytest.mark.parametrize("input_date, expected_iso, expected_amended", [
        ("24 June 2026", "2026-06-24", 0),
        ("24 Jun 2026", "2026-06-24", 0),
        ("24/06/2026", "2026-06-24", 0),
        ("24 June 202 6 (amended)", "2026-06-24", 1),
        ("re-issued 15 December 2024", "2024-12-15", 1),
        ("20 December 2024 (amended at review)", "2024-12-20", 1),
        ("invalid date", None, 0),
        ("", None, 0),
        (None, None, 0),
    ])
    def test_clean_date_to_iso(self, input_date, expected_iso, expected_amended):
        iso_val, amended_val = clean_date_to_iso(input_date)
        assert iso_val == expected_iso
        assert amended_val == expected_amended
