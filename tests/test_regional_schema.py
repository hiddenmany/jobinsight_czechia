
import pytest
import os
import sys
import tempfile
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
from analyzer import IntelligenceCore, JobSignal

class TestRegionalSchema:
    @pytest.fixture
    def temp_db(self, tmp_path):
        db_path = str(tmp_path / "test_regional.db")
        import analyzer
        original_path = analyzer.DB_PATH
        analyzer.DB_PATH = db_path
        yield db_path
        analyzer.DB_PATH = original_path

    @pytest.fixture
    def core(self, temp_db):
        return IntelligenceCore(read_only=False)

    def test_schema_includes_region_and_city(self, core):
        """Verify that the signals table includes region and city columns."""
        # Get column info
        columns = core.con.execute("PRAGMA table_info('signals')").fetchall()
        column_names = [col[1] for col in columns]
        
        assert "region" in column_names, f"Column 'region' missing from signals table. Found: {column_names}"
        assert "city" in column_names, f"Column 'city' missing from signals table. Found: {column_names}"

    def test_add_signal_normalizes_region(self, core):
        """Verify that add_signal normalizes the region based on location."""
        sample = JobSignal(
            title="Dev",
            company="Test",
            link="http://test.com/prague",
            source="Test",
            location="Praha 4"
        )
        
        core.add_signal(sample)
        
        result = core.con.execute("SELECT region, city FROM signals WHERE link = ?", [sample.link]).fetchone()
        assert result is not None
        assert result[0] == "Prague"
        assert result[1] == "Prague"

    def test_add_signal_normalizes_brno(self, core):
        """Verify that add_signal normalizes Brno locations."""
        sample = JobSignal(
            title="Dev",
            company="Test",
            link="http://test.com/brno",
            source="Test",
            location="Brno-střed"
        )
        
        core.add_signal(sample)
        
        result = core.con.execute("SELECT region, city FROM signals WHERE link = ?", [sample.link]).fetchone()
        assert result is not None
        assert result[0] == "Brno"
        assert result[1] == "Brno"
