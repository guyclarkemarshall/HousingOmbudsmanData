#!/usr/bin/env python3
"""
Tests for verify_insights.py verification script.
Tests that the new verification sections output correctly.
"""

import sqlite3
import pytest
from verify_insights import verify_insights_db
from build_insights_db import init_dest_db


def add_minimal_data(db_path):
    """Helper to add minimal data needed to avoid division by zero in existing code."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
    landlord_id = cursor.lastrowid
    cursor.execute(
        """INSERT INTO cases
           (case_id, url, title, decision_date, landlord_id, stage_1_days_est, stage_2_days_est)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, 30, 60),
    )
    cursor.execute(
        """INSERT INTO issues
           (case_id, description, determination, category)
           VALUES (?, ?, ?, ?)""",
        ("case_001", "Test issue", "No Maladministration", "Repairs"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def tmp_db(tmp_path):
    """Initializes a temporary database with the insights schema.

    All tests reuse the same initialized database to avoid repeated initialization.
    """
    db_path = str(tmp_path / "test_insights.db")
    init_dest_db(db_path)  # Initialize schema
    yield db_path
    # Cleanup happens automatically via tmp_path fixture


class TestDocumentFormatDistribution:
    """Test section 9: Document format distribution."""

    def test_document_format_section_prints(self, tmp_db, capsys):
        """Verify that document format section prints header."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        assert "=== DOCUMENT FORMAT DISTRIBUTION ===" in captured.out

    def test_document_format_with_empty_table(self, tmp_db, capsys):
        """Verify script runs without error when cases table has data but minimal schema."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        # Should complete without raising an exception
        assert "=== DOCUMENT FORMAT DISTRIBUTION ===" in captured.out

    def test_document_format_with_data(self, tmp_db, capsys):
        """Verify document format distribution with actual data."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases with different doc formats
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, doc_format, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, "PDF", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, doc_format, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, "HTML", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, doc_format, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_003", "http://test.com/003", "Test Case 3", "2024-01-03", landlord_id, "PDF", 30, 60),
        )

        # Add at least one issue to avoid division by zero in existing code
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== DOCUMENT FORMAT DISTRIBUTION ===" in captured.out
        assert "PDF" in captured.out or "pdf" in captured.out.lower()
        assert "HTML" in captured.out or "html" in captured.out.lower()


class TestLandlordTypeDistribution:
    """Test section 10: Landlord type distribution."""

    def test_landlord_type_section_prints(self, tmp_db, capsys):
        """Verify that landlord type section prints header."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out

    def test_landlord_type_with_empty_table(self, tmp_db, capsys):
        """Verify script runs without error when no landlord types exist."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        # Should complete without raising an exception
        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out
        assert "NULL (not extracted)" in captured.out

    def test_landlord_type_with_null_values(self, tmp_db, capsys):
        """Verify landlord type handles NULL values gracefully."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases with NULL landlord_type
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, landlord_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, None, 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, landlord_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, None, 30, 60),
        )

        # Add at least one issue to avoid division by zero
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out
        assert "NULL (not extracted)" in captured.out
        # Should show 2 NULL cases
        assert "2" in captured.out

    def test_landlord_type_with_mixed_data(self, tmp_db, capsys):
        """Verify landlord type distribution with mixed NULL and non-NULL data."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases with mixed landlord types
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, landlord_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, "Local Authority", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, landlord_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, "Housing Association", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, landlord_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_003", "http://test.com/003", "Test Case 3", "2024-01-03", landlord_id, None, 30, 60),
        )

        # Add at least one issue to avoid division by zero
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out
        assert "Local Authority" in captured.out
        assert "Housing Association" in captured.out
        assert "NULL (not extracted)" in captured.out


class TestTenancyTypeDistribution:
    """Test section 10b: Tenancy type distribution."""

    def test_tenancy_type_section_prints(self, tmp_db, capsys):
        """Verify that tenancy type section prints header."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out

    def test_tenancy_type_with_empty_table(self, tmp_db, capsys):
        """Verify script runs without error when no tenancy types exist."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        # Should complete without raising an exception
        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out
        assert "NULL (not extracted)" in captured.out

    def test_tenancy_type_with_null_values(self, tmp_db, capsys):
        """Verify tenancy type handles NULL values gracefully."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases with NULL tenancy_type
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, None, 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, None, 30, 60),
        )

        # Add at least one issue to avoid division by zero
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out
        assert "NULL (not extracted)" in captured.out

    def test_tenancy_type_with_mixed_data(self, tmp_db, capsys):
        """Verify tenancy type distribution with mixed NULL and non-NULL data."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases with mixed tenancy types
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, "Assured Shorthold", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, "Secure", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_003", "http://test.com/003", "Test Case 3", "2024-01-03", landlord_id, None, 30, 60),
        )

        # Add at least one issue to avoid division by zero
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out
        assert "Assured Shorthold" in captured.out
        assert "Secure" in captured.out
        assert "NULL (not extracted)" in captured.out


class TestLegalCitations:
    """Test section 11: Legal citations."""

    def test_legal_citations_section_prints(self, tmp_db, capsys):
        """Verify that legal citations section prints header."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        assert "=== LEGAL CITATIONS (TOP 15) ===" in captured.out
        assert "Total citation records:" in captured.out

    def test_legal_citations_with_empty_table(self, tmp_db, capsys):
        """Verify script runs without error when legal_citations table is empty."""
        add_minimal_data(tmp_db)

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()
        # Should complete without raising an exception
        assert "=== LEGAL CITATIONS (TOP 15) ===" in captured.out
        assert "Total citation records: 0" in captured.out

    def test_legal_citations_with_data(self, tmp_db, capsys):
        """Verify legal citations distribution with actual data."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        # Insert test landlord
        cursor.execute("INSERT INTO landlords (name) VALUES ('Test Landlord')")
        landlord_id = cursor.lastrowid

        # Insert test cases
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id, 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id, 30, 60),
        )

        # Insert at least one issue to avoid division by zero
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category)
               VALUES (?, ?, ?, ?)""",
            ("case_001", "Test issue", "No Maladministration", "Repairs"),
        )

        # Insert legal citations
        cursor.execute(
            "INSERT INTO legal_citations (case_id, statute) VALUES (?, ?)",
            ("case_001", "Housing Act 1985"),
        )
        cursor.execute(
            "INSERT INTO legal_citations (case_id, statute) VALUES (?, ?)",
            ("case_001", "Housing Act 1988"),
        )
        cursor.execute(
            "INSERT INTO legal_citations (case_id, statute) VALUES (?, ?)",
            ("case_002", "Housing Act 1985"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        assert "=== LEGAL CITATIONS (TOP 15) ===" in captured.out
        assert "Total citation records: 3" in captured.out
        assert "Housing Act 1985" in captured.out
        assert "Housing Act 1988" in captured.out


class TestFullIntegration:
    """Integration tests for the complete verify_insights_db function."""

    def test_full_verification_runs_without_error(self, tmp_db, capsys):
        """Verify that the complete verification script runs without error."""
        # Add minimal data to avoid division by zero
        add_minimal_data(tmp_db)
        # Should not raise any exception
        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        # Verify all major sections are present
        assert "=== RECORD COUNTS ===" in captured.out
        assert "=== ISSUE CATEGORY DISTRIBUTION ===" in captured.out
        assert "=== DETERMINATION DISTRIBUTION ===" in captured.out
        assert "=== COMPLAINT UPHELD RATES ===" in captured.out
        assert "=== OMBUDSMAN REMEDIES & ORDERS (CASE LEVEL) ===" in captured.out
        assert "=== OPERATIONAL CONTEXT FLAGS (CASE LEVEL) ===" in captured.out
        assert "=== COMPLAINT TIMESCALE STATS ===" in captured.out
        assert "=== FINANCIAL ORDERS STATS ===" in captured.out
        assert "=== TOP 5 LANDLORDS BY MALADMINISTRATION ISSUE COUNT ===" in captured.out
        # New sections
        assert "=== DOCUMENT FORMAT DISTRIBUTION ===" in captured.out
        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out
        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out
        assert "=== LEGAL CITATIONS (TOP 15) ===" in captured.out

    def test_full_verification_with_comprehensive_data(self, tmp_db, capsys):
        """Verify complete verification with comprehensive test data."""
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Insert test landlords
        cursor.execute("INSERT INTO landlords (name) VALUES ('Landlord A')")
        landlord_id_a = cursor.lastrowid
        cursor.execute("INSERT INTO landlords (name) VALUES ('Landlord B')")
        landlord_id_b = cursor.lastrowid

        # Insert test cases
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id,
                total_compensation_ordered, is_upheld_est,
                doc_format, landlord_type, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_001", "http://test.com/001", "Test Case 1", "2024-01-01", landlord_id_a,
             1000.0, 1, "PDF", "Local Authority", "Secure", 30, 60),
        )
        cursor.execute(
            """INSERT INTO cases
               (case_id, url, title, decision_date, landlord_id,
                total_compensation_ordered, is_upheld_est,
                doc_format, landlord_type, tenancy_type, stage_1_days_est, stage_2_days_est)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("case_002", "http://test.com/002", "Test Case 2", "2024-01-02", landlord_id_b,
             500.0, 0, "HTML", "Housing Association", "Assured Shorthold", 30, 60),
        )

        # Insert issues
        cursor.execute(
            """INSERT INTO issues
               (case_id, description, determination, category, is_upheld_est)
               VALUES (?, ?, ?, ?, ?)""",
            ("case_001", "Test issue 1", "Maladministration", "Repairs", 1),
        )

        # Insert compensation orders
        cursor.execute(
            "INSERT INTO compensation_orders (case_id, amount, description) VALUES (?, ?, ?)",
            ("case_001", 1000.0, "Compensation for repairs"),
        )

        # Insert legal citations
        cursor.execute(
            "INSERT INTO legal_citations (case_id, statute) VALUES (?, ?)",
            ("case_001", "Housing Act 1985"),
        )
        cursor.execute(
            "INSERT INTO legal_citations (case_id, statute) VALUES (?, ?)",
            ("case_002", "Housing Act 1988"),
        )

        conn.commit()
        conn.close()

        verify_insights_db(tmp_db)
        captured = capsys.readouterr()

        # Verify that all sections completed
        assert "=== DOCUMENT FORMAT DISTRIBUTION ===" in captured.out
        assert "=== LANDLORD TYPE DISTRIBUTION ===" in captured.out
        assert "=== TENANCY TYPE DISTRIBUTION ===" in captured.out
        assert "=== LEGAL CITATIONS (TOP 15) ===" in captured.out
