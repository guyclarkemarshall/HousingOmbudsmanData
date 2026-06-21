#!/usr/bin/env python3
"""
Tests for the insights database schema initialization.
Verifies that init_dest_db creates the correct tables, columns, and indexes.
"""

import sqlite3
import os
import pytest
from build_insights_db import init_dest_db


@pytest.fixture
def tmp_db(tmp_path):
    """Initializes a temporary database once and yields the path.

    All tests reuse the same initialized database to avoid repeated initialization.
    """
    db_path = str(tmp_path / "test_insights.db")
    init_dest_db(db_path)  # Initialize once
    yield db_path
    # Cleanup happens automatically via tmp_path fixture


class TestCasesTableColumns:
    """Test that the cases table has all required columns."""

    def test_cases_table_has_doc_format_column(self, tmp_db):
        """Verify cases table includes doc_format column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name -> type

        assert "doc_format" in columns
        assert columns["doc_format"] == "TEXT"
        conn.close()

    def test_cases_table_has_landlord_type_column(self, tmp_db):
        """Verify cases table includes landlord_type column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "landlord_type" in columns
        assert columns["landlord_type"] == "TEXT"
        conn.close()

    def test_cases_table_has_tenancy_type_column(self, tmp_db):
        """Verify cases table includes tenancy_type column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "tenancy_type" in columns
        assert columns["tenancy_type"] == "TEXT"
        conn.close()


class TestLegalCitationsTable:
    """Test that legal_citations table is created with correct structure."""

    def test_legal_citations_table_exists(self, tmp_db):
        """Verify legal_citations table is created."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='legal_citations'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()

    def test_legal_citations_has_id_column(self, tmp_db):
        """Verify legal_citations table has id column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(legal_citations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "id" in columns
        assert columns["id"] == "INTEGER"
        conn.close()

    def test_legal_citations_has_case_id_column(self, tmp_db):
        """Verify legal_citations table has case_id column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(legal_citations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "case_id" in columns
        assert columns["case_id"] == "TEXT"
        conn.close()

    def test_legal_citations_has_statute_column(self, tmp_db):
        """Verify legal_citations table has statute column."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(legal_citations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "statute" in columns
        assert columns["statute"] == "TEXT"
        conn.close()


class TestIndexes:
    """Test that required indexes are created."""

    def test_idx_citations_case_exists(self, tmp_db):
        """Verify idx_citations_case index exists."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_citations_case'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()

    def test_idx_citations_statute_exists(self, tmp_db):
        """Verify idx_citations_statute index exists."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_citations_statute'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()


class TestForeignKeyConstraints:
    """Test that foreign key constraints are properly defined."""

    def test_legal_citations_case_id_fk_constraint_exists(self, tmp_db):
        """Verify legal_citations.case_id has a foreign key constraint."""
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_key_list(legal_citations)")
        fk_list = cursor.fetchall()

        # fk_list is a list of (id, seq, table, from, to, on_update, on_delete, match)
        # We expect at least one FK with case_id referencing cases.case_id
        fk_found = any(
            fk[3] == "case_id" and fk[2] == "cases" and fk[4] == "case_id"
            for fk in fk_list
        )

        assert fk_found, "Foreign key constraint on legal_citations.case_id not found"
        conn.close()


class TestCascadeDelete:
    """Test that ON DELETE CASCADE behavior works correctly."""

    def test_cascade_delete_citation_when_case_deleted(self, tmp_db):
        """Verify that deleting a case cascades to delete its citations."""
        conn = sqlite3.connect(tmp_db)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Insert a test case
        cursor.execute(
            """
            INSERT INTO cases (case_id, url, title, decision_date, landlord_id)
            VALUES (?, ?, ?, ?, NULL)
            """,
            ("test_case_001", "http://test.example.com", "Test Case", "2024-01-01"),
        )

        # Insert a legal citation referencing the case
        cursor.execute(
            """
            INSERT INTO legal_citations (case_id, statute)
            VALUES (?, ?)
            """,
            ("test_case_001", "Housing Act 1985"),
        )

        conn.commit()

        # Verify citation was inserted
        cursor.execute(
            "SELECT COUNT(*) FROM legal_citations WHERE case_id = ?",
            ("test_case_001",),
        )
        citation_count_before = cursor.fetchone()[0]
        assert citation_count_before == 1, "Citation was not inserted"

        # Delete the case
        cursor.execute("DELETE FROM cases WHERE case_id = ?", ("test_case_001",))
        conn.commit()

        # Verify citation was cascaded deleted
        cursor.execute(
            "SELECT COUNT(*) FROM legal_citations WHERE case_id = ?",
            ("test_case_001",),
        )
        citation_count_after = cursor.fetchone()[0]
        assert (
            citation_count_after == 0
        ), "Citation was not deleted when parent case was deleted (ON DELETE CASCADE not working)"

        conn.close()
