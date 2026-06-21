"""
Tests for extract_compensation in build_insights_db.py

TDD: Tests written BEFORE the implementation is replaced.
Tests exercise the new section-dict interface and verify removal of the £10k cap.
"""
import os
import sys
import pytest

# Adjust import path so project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_insights_db import extract_compensation


class TestExtractCompensationBounds:
    """Tests for the amount bounds (£5 minimum, no maximum)."""

    def test_amounts_below_5_are_excluded(self):
        """Amounts below £5 are excluded (e.g. £3 → not included)."""
        sections = {
            'orders': 'The landlord must pay £3 for the breach. This is negligible.'
        }
        total, items = extract_compensation(sections)
        assert total == 0.0
        assert items == []

    def test_amounts_exactly_5_are_included(self):
        """Amounts of exactly £5 are included."""
        sections = {
            'orders': 'The landlord must pay £5 to the resident.'
        }
        total, items = extract_compensation(sections)
        assert total == 5.0
        assert len(items) == 1
        assert items[0][0] == 5.0

    def test_amounts_above_10k_are_included(self):
        """Amounts above £10,000 ARE included (main fix for Task 5)."""
        sections = {
            'orders_1': 'The landlord must pay £15,000 to the resident.'
        }
        total, items = extract_compensation(sections)
        assert total == 15000.0
        assert len(items) == 1
        assert items[0][0] == 15000.0

    def test_very_large_amount_above_50k_included(self):
        """Large amounts (>£50k) without 'claim' in sentence are included."""
        sections = {
            'orders': 'The landlord must pay £86,831 as compensation for the serious breach.'
        }
        total, items = extract_compensation(sections)
        assert total == 86831.0
        assert len(items) == 1
        assert items[0][0] == 86831.0

    def test_large_amount_with_claim_keyword_excluded(self):
        """Amounts above £50,000 with 'claim' in the sentence are excluded (likely claim references)."""
        sections = {
            'orders': 'The resident claimed £75,000 for damages but the landlord disputed it.'
        }
        total, items = extract_compensation(sections)
        # The match contains 'claim' so should be filtered out
        assert total == 0.0
        assert items == []

    def test_large_amount_without_claim_keyword_included(self):
        """Amounts above £50,000 without 'claim' in the sentence ARE included."""
        sections = {
            'orders': 'The landlord must pay £60,000 compensation for the serious breach and distress.'
        }
        total, items = extract_compensation(sections)
        assert total == 60000.0
        assert len(items) == 1


class TestExtractCompensationSectionPreference:
    """Tests for section fallback order."""

    def test_prefers_orders_and_recommendations(self):
        """Prefers 'orders_and_recommendations' section over 'full_doc'."""
        sections = {
            'orders_and_recommendations': 'The landlord must pay £1000.',
            'full_doc': 'Some other text with £999999 that should be ignored.'
        }
        total, items = extract_compensation(sections)
        assert total == 1000.0
        assert len(items) == 1

    def test_fallback_to_orders_1(self):
        """Falls back to 'orders_1' if 'orders_and_recommendations' not present."""
        sections = {
            'orders_1': 'The landlord must pay £500.',
            'full_doc': 'Some text with other amounts.'
        }
        total, items = extract_compensation(sections)
        assert total == 500.0

    def test_fallback_to_orders(self):
        """Falls back to 'orders' if earlier sections not present."""
        sections = {
            'orders': 'The landlord must pay £250.',
        }
        total, items = extract_compensation(sections)
        assert total == 250.0

    def test_fallback_to_putting_things_right_1(self):
        """Falls back to 'putting_things_right_1' if orders sections not present."""
        sections = {
            'putting_things_right_1': 'The landlord must pay £100.',
        }
        total, items = extract_compensation(sections)
        assert total == 100.0

    def test_fallback_to_putting_things_right(self):
        """Falls back to 'putting_things_right' if other orders sections not present."""
        sections = {
            'putting_things_right': 'The landlord must pay £75.',
        }
        total, items = extract_compensation(sections)
        assert total == 75.0

    def test_fallback_to_full_doc(self):
        """Falls back to 'full_doc' if no orders section found."""
        sections = {
            'full_doc': 'The landlord must pay £50.',
        }
        total, items = extract_compensation(sections)
        assert total == 50.0


class TestExtractCompensationEmptyInput:
    """Tests for empty/missing sections."""

    def test_returns_zero_for_empty_dict(self):
        """Returns (0.0, []) for empty sections dict."""
        total, items = extract_compensation({})
        assert total == 0.0
        assert items == []

    def test_returns_zero_when_no_amounts_found(self):
        """Returns (0.0, []) when orders section has no monetary amounts."""
        sections = {
            'orders': 'The landlord must make certain repairs.'
        }
        total, items = extract_compensation(sections)
        assert total == 0.0
        assert items == []


class TestExtractCompensationMultipleAmounts:
    """Tests for aggregating multiple compensation amounts."""

    def test_sums_multiple_amounts(self):
        """Total is the sum of all included amounts."""
        sections = {
            'orders': (
                'The landlord must pay £100 for the breach. '
                'Additionally, £250 must be paid for distress. '
                'Furthermore, £650 is ordered.'
            )
        }
        total, items = extract_compensation(sections)
        assert total == 1000.0
        assert len(items) == 3

    def test_includes_multiple_large_amounts(self):
        """Multiple large amounts (all >£10k) are correctly summed."""
        sections = {
            'orders': (
                'The landlord must pay £15,000 for the failure. '
                'An additional £20,000 is ordered for distress. '
                'Furthermore, £10,001 must be paid.'
            )
        }
        total, items = extract_compensation(sections)
        assert total == 45001.0
        assert len(items) == 3


class TestExtractCompensationBackwardCompatibility:
    """Tests for backward compatibility with old string-based interface."""

    def test_accepts_string_input_for_backward_compat(self):
        """Accepts a string (full_doc) for backward compatibility with old call site."""
        text = 'The landlord must pay £500.'
        total, items = extract_compensation(text)
        assert total == 500.0
        assert len(items) == 1

    def test_string_input_treated_as_full_doc(self):
        """String input is treated as the full_doc fallback."""
        text = 'Some header. The landlord must pay £200. Some footer.'
        total, items = extract_compensation(text)
        assert total == 200.0


class TestExtractCompensationItemDescriptions:
    """Tests for the item descriptions in the return list."""

    def test_items_include_sentence_text(self):
        """Each item is a tuple of (amount, sentence[:250])."""
        sections = {
            'orders': 'The landlord must pay £1000 for the serious breach and distress caused.'
        }
        total, items = extract_compensation(sections)
        assert len(items) == 1
        amount, description = items[0]
        assert amount == 1000.0
        assert isinstance(description, str)
        assert '£' in description or 'breach' in description  # Should contain context

    def test_description_truncated_to_250_chars(self):
        """Description is truncated to at most 250 characters."""
        sections = {
            'orders': 'The landlord must pay £500 ' + 'x' * 300
        }
        total, items = extract_compensation(sections)
        assert len(items) == 1
        amount, description = items[0]
        assert len(description) <= 250
