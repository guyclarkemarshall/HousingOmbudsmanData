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
    """Creates a temporary database file for testing."""
    db_path = str(tmp_path / "test_insights.db")
    yield db_path
    # Cleanup happens automatically via tmp_path fixture


class TestCasesTableColumns:
    """Test that the cases table has all required columns."""

    def test_cases_table_has_doc_format_column(self, tmp_db):
        """Verify cases table includes doc_format column."""
        init_dest_db(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name -> type

        assert "doc_format" in columns
        assert columns["doc_format"] == "TEXT"
        conn.close()

    def test_cases_table_has_landlord_type_column(self, tmp_db):
        """Verify cases table includes landlord_type column."""
        init_dest_db(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(cases)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "landlord_type" in columns
        assert columns["landlord_type"] == "TEXT"
        conn.close()

    def test_cases_table_has_tenancy_type_column(self, tmp_db):
        """Verify cases table includes tenancy_type column."""
        init_dest_db(tmp_db)
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
        init_dest_db(tmp_db)
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
        init_dest_db(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(legal_citations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "id" in columns
        assert columns["id"] == "INTEGER"
        conn.close()

    def test_legal_citations_has_case_id_column(self, tmp_db):
        """Verify legal_citations table has case_id column."""
        init_dest_db(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(legal_citations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "case_id" in columns
        assert columns["case_id"] == "TEXT"
        conn.close()

    def test_legal_citations_has_statute_column(self, tmp_db):
        """Verify legal_citations table has statute column."""
        init_dest_db(tmp_db)
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
        init_dest_db(tmp_db)
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
        init_dest_db(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_citations_statute'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()
