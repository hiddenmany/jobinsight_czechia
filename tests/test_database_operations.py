"""
Stage 4: Database Operation Tests for IntelligenceCore.

Tests critical database methods including:
- is_known (atomic duplicate detection)
- add_signal (signal insertion with enrichment)
- cleanup_expired (stale record removal)
- get_database_stats (monitoring)
"""

import pytest
import sys
import os
import tempfile
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use temp database for testing
import duckdb


class TestIntelligenceCore:
    """Tests for IntelligenceCore database operations."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database path for testing."""
        # Use pytest's tmp_path fixture for proper temp directory
        db_path = str(tmp_path / "test_intelligence.db")
        
        # Patch the DB_PATH before importing
        import analyzer
        original_path = analyzer.DB_PATH
        analyzer.DB_PATH = db_path
        
        yield db_path
        
        # Cleanup - restore original path
        analyzer.DB_PATH = original_path

    @pytest.fixture
    def core(self, temp_db):
        """Create IntelligenceCore with temp database."""
        from analyzer import IntelligenceCore
        return IntelligenceCore(read_only=False)

    @pytest.fixture
    def sample_signal(self):
        """Create a sample JobSignal for testing."""
        from analyzer import JobSignal
        return JobSignal(
            title="Python Developer",
            company="TestCo",
            link="https://example.com/job/123",
            source="TestSource",
            salary="50000 Kč",
            description="Python and Django experience required.",
            benefits="Remote, Flexible hours",
            location="Praha"
        )

    def test_is_known_returns_false_for_new_url(self, core):
        """is_known should return False for URLs not in database."""
        assert not core.is_known("https://nonexistent.com/job/999")

    def test_is_known_returns_true_after_add(self, core, sample_signal):
        """is_known should return True after signal is added."""
        core.add_signal(sample_signal)
        assert core.is_known(sample_signal.link)

    def test_add_signal_creates_record(self, core, sample_signal):
        """add_signal should insert a record into the database."""
        core.add_signal(sample_signal)
        
        # Query directly to verify
        result = core.con.execute(
            "SELECT title, company FROM signals WHERE link = ?",
            [sample_signal.link]
        ).fetchone()
        
        assert result is not None
        assert result[0] == sample_signal.title
        assert result[1] == sample_signal.company

    def test_add_signal_enriches_with_role(self, core, sample_signal):
        """add_signal should classify role type."""
        core.add_signal(sample_signal)
        
        result = core.con.execute(
            "SELECT role_type FROM signals WHERE link = ?",
            [sample_signal.link]
        ).fetchone()
        
        assert result is not None
        assert result[0] == "Developer"  # Python Developer -> Developer

    def test_add_signal_enriches_with_seniority(self, core):
        """add_signal should detect seniority level."""
        from analyzer import JobSignal
        senior_signal = JobSignal(
            title="Senior Python Developer",
            company="TestCo",
            link="https://example.com/job/senior",
            source="TestSource"
        )
        core.add_signal(senior_signal)
        
        result = core.con.execute(
            "SELECT seniority_level FROM signals WHERE link = ?",
            [senior_signal.link]
        ).fetchone()
        
        assert result is not None
        assert result[0] == "Senior"

    def test_add_signal_deduplicates_by_hash(self, core, sample_signal):
        """Duplicate content should not create duplicate records."""
        core.add_signal(sample_signal)
        core.add_signal(sample_signal)  # Add again
        
        count = core.con.execute(
            "SELECT COUNT(*) FROM signals WHERE link = ?",
            [sample_signal.link]
        ).fetchone()[0]
        
        assert count == 1

    def test_cleanup_expired_removes_old_records(self, core, sample_signal):
        """cleanup_expired should remove records older than threshold."""
        core.add_signal(sample_signal)
        
        # Manually set last_seen_at to 2 hours ago
        old_time = datetime.now() - timedelta(hours=2)
        core.con.execute(
            "UPDATE signals SET last_seen_at = ? WHERE link = ?",
            [old_time, sample_signal.link]
        )
        
        # Cleanup records older than 60 minutes
        core.cleanup_expired(threshold_minutes=60)
        
        # Record should be gone
        result = core.con.execute(
            "SELECT COUNT(*) FROM signals WHERE link = ?",
            [sample_signal.link]
        ).fetchone()[0]
        
        assert result == 0

    def test_cleanup_expired_keeps_recent_records(self, core, sample_signal):
        """cleanup_expired should keep records newer than threshold."""
        core.add_signal(sample_signal)
        
        # Cleanup with 120 minute threshold (record is fresh)
        core.cleanup_expired(threshold_minutes=120)
        
        # Record should still exist
        result = core.con.execute(
            "SELECT COUNT(*) FROM signals WHERE link = ?",
            [sample_signal.link]
        ).fetchone()[0]
        
        assert result == 1

    def test_cleanup_expired_validates_threshold(self, core):
        """cleanup_expired should raise error for invalid threshold."""
        with pytest.raises(ValueError):
            core.cleanup_expired(threshold_minutes=-1)

    def test_get_database_stats_returns_dict(self, core):
        """get_database_stats should return a dict with expected keys."""
        stats = core.get_database_stats()
        
        assert isinstance(stats, dict)
        assert 'total_jobs' in stats
        assert 'db_size_mb' in stats
        assert 'by_source' in stats

    def test_get_database_stats_counts_records(self, core, sample_signal):
        """get_database_stats should accurately count records."""
        initial_stats = core.get_database_stats()
        initial_count = initial_stats['total_jobs']
        
        core.add_signal(sample_signal)
        
        new_stats = core.get_database_stats()
        assert new_stats['total_jobs'] == initial_count + 1

    def test_vacuum_database_runs_without_error(self, core):
        """vacuum_database should complete without raising exceptions."""
        # Just verify it doesn't crash
        core.vacuum_database()
