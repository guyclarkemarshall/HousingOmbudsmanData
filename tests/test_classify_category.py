"""
Tests for classify_category function from build_insights_db.py
Tests verify the correct reordering so that 'Complaint Handling' only fires as a residual.
"""

import pytest
from build_insights_db import classify_category


class TestClassifyCategory:
    """Test suite for classify_category function."""

    def test_damp_and_mould(self):
        """Test that damp/mould descriptions are classified correctly."""
        desc = "landlord's handling of damp and mould"
        assert classify_category(desc) == "Damp & Mould"

    def test_repairs_and_maintenance_no_complaint_handling(self):
        """Test that repair issues don't get incorrectly classified as Complaint Handling.
        This is the key test — if 'Complaint Handling' fires too early, this will fail."""
        desc = "landlord's handling of the repair to the boiler"
        assert classify_category(desc) == "Repairs & Maintenance"

    def test_complaint_handling_residual(self):
        """Test that Complaint Handling only fires when no specific match exists."""
        desc = "landlord's complaint handling at stage 2"
        assert classify_category(desc) == "Complaint Handling"

    def test_pest_control(self):
        """Test that pest/infestation issues are classified correctly."""
        desc = "landlord's response to reports of mice infestation"
        assert classify_category(desc) == "Pest Control"

    def test_rehousing_and_allocations(self):
        """Test that rehousing/allocation issues are classified correctly."""
        desc = "landlord's handling of the resident's transfer request"
        assert classify_category(desc) == "Rehousing & Allocations"

    def test_leaks_and_water_ingress(self):
        """Test that leak/water issues are classified correctly."""
        desc = "landlord's handling of the water leak from the roof"
        assert classify_category(desc) == "Leaks & Water Ingress"

    def test_anti_social_behaviour(self):
        """Test that anti-social behaviour issues are classified correctly."""
        desc = "landlord's response to anti-social behaviour"
        assert classify_category(desc) == "Anti-Social Behaviour (ASB)"

    def test_estate_management(self):
        """Test that estate management issues are classified correctly."""
        desc = "landlord's management of communal areas"
        assert classify_category(desc) == "Estate Management"

    def test_rent_and_service_charges(self):
        """Test that rent/billing issues are classified correctly."""
        desc = "landlord's handling of rent arrears"
        assert classify_category(desc) == "Rent & Service Charges"

    def test_other_default(self):
        """Test that unmatched descriptions return 'Other'."""
        desc = "landlord's procedure for something completely unrelated"
        assert classify_category(desc) == "Other"
