"""
Unit tests for job manager implementation.

Tests the RedisJobManager class for proper job creation,
status transitions, and job querying functionality.

Validates: Requirements 6.1, 6.2, 6.3, 6.5, 6.6
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from app.services.job_manager import IJobManager, RedisJobManager
from app.models.enums import JobStatus


class FakeRedis:
    """
    Fake Redis implementation for testing without a real Redis server.
    
    Implements the subset of Redis commands used by RedisJobManager.
    """
    
    def __init__(self):
        self._data = {}  # Hash storage
        self._sets = {}  # Set storage
    
    def hset(self, key, mapping=None, **kwargs):
        """Set hash fields."""
        if key not in self._data:
            self._data[key] = {}
        if mapping:
            self._data[key].update(mapping)
        self._data[key].update(kwargs)
    
    def hget(self, key, field):
        """Get a hash field."""
        if key in self._data and field in self._data[key]:
            return self._data[key][field]
        return None
    
    def hgetall(self, key):
        """Get all hash fields."""
        return self._data.get(key, {})
    
    def exists(self, key):
        """Check if key exists."""
        return key in self._data
    
    def delete(self, key):
        """Delete a key."""
        if key in self._data:
            del self._data[key]
            return 1
        return 0
    
    def sadd(self, key, *values):
        """Add to set."""
        if key not in self._sets:
            self._sets[key] = set()
        for v in values:
            self._sets[key].add(v)
        return len(values)
    
    def srem(self, key, *values):
        """Remove from set."""
        if key not in self._sets:
            return 0
        removed = 0
        for v in values:
            if v in self._sets[key]:
                self._sets[key].remove(v)
                removed += 1
        return removed
    
    def smembers(self, key):
        """Get all set members."""
        return self._sets.get(key, set())


@pytest.fixture
def fake_redis():
    """Create a fake Redis instance for testing."""
    return FakeRedis()


@pytest.fixture
def job_manager(fake_redis):
    """Create a RedisJobManager with fake Redis."""
    return RedisJobManager(redis_client=fake_redis)


class TestRedisJobManager:
    """Test suite for RedisJobManager implementation."""
    
    def test_implements_interface(self, job_manager):
        """Verify RedisJobManager implements IJobManager interface."""
        assert isinstance(job_manager, IJobManager)
    
    def test_create_job_returns_unique_id(self, job_manager):
        """
        Test that create_job returns a unique job ID.
        
        Validates: Requirements 6.1
        """
        job_id_1 = job_manager.create_job("caption_generation", "video-123")
        job_id_2 = job_manager.create_job("caption_generation", "video-123")
        job_id_3 = job_manager.create_job("video_processing", "video-456")
        
        assert job_id_1 != job_id_2
        assert job_id_2 != job_id_3
        assert job_id_1 != job_id_3
    
    def test_create_job_sets_pending_status(self, job_manager):
        """
        Test that create_job initializes job with pending status.
        
        Validates: Requirements 6.1
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job = job_manager.get_job(job_id)
        
        assert job is not None
        assert job["status"] == JobStatus.PENDING
    
    def test_create_job_stores_job_type_and_video_id(self, job_manager):
        """
        Test that create_job stores job type and video ID correctly.
        
        Validates: Requirements 6.1
        """
        job_id = job_manager.create_job("video_processing", "video-789")
        job = job_manager.get_job(job_id)
        
        assert job["job_type"] == "video_processing"
        assert job["video_id"] == "video-789"
    
    def test_create_job_sets_timestamps(self, job_manager):
        """
        Test that create_job sets created_at and updated_at timestamps.
        
        Validates: Requirements 6.1
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job = job_manager.get_job(job_id)
        
        assert job["created_at"] is not None
        assert job["updated_at"] is not None
        assert isinstance(job["created_at"], datetime)
        assert isinstance(job["updated_at"], datetime)

    def test_update_status_to_processing(self, job_manager):
        """
        Test updating job status from pending to processing.
        
        Validates: Requirements 6.2
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        
        job = job_manager.get_job(job_id)
        assert job["status"] == JobStatus.PROCESSING
    
    def test_update_status_to_completed(self, job_manager):
        """
        Test updating job status from processing to completed.
        
        Validates: Requirements 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        
        job_manager.update_status(
            job_id, 
            JobStatus.COMPLETED, 
            result="/outputs/video-123.mp4"
        )
        
        job = job_manager.get_job(job_id)
        assert job["status"] == JobStatus.COMPLETED
        assert job["result_path"] == "/outputs/video-123.mp4"
    
    def test_update_status_to_failed(self, job_manager):
        """
        Test updating job status from processing to failed.
        
        Validates: Requirements 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        
        job_manager.update_status(
            job_id, 
            JobStatus.FAILED, 
            error="Audio extraction failed"
        )
        
        job = job_manager.get_job(job_id)
        assert job["status"] == JobStatus.FAILED
        assert job["error_message"] == "Audio extraction failed"
    
    def test_update_status_with_progress(self, job_manager):
        """
        Test updating job status with progress percentage.
        
        Validates: Requirements 6.2
        """
        job_id = job_manager.create_job("video_processing", "video-123")
        job_manager.update_status(job_id, JobStatus.PROCESSING, progress=50)
        
        job = job_manager.get_job(job_id)
        assert job["progress"] == 50
    
    def test_update_status_updates_timestamp(self, job_manager):
        """
        Test that update_status updates the updated_at timestamp.
        
        Validates: Requirements 6.2
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job_before = job_manager.get_job(job_id)
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        job_after = job_manager.get_job(job_id)
        
        assert job_after["updated_at"] >= job_before["updated_at"]
    
    def test_invalid_transition_pending_to_completed(self, job_manager):
        """
        Test that invalid status transition raises error.
        
        Validates: Requirements 6.2, 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_manager.update_status(job_id, JobStatus.COMPLETED)
    
    def test_invalid_transition_pending_to_failed(self, job_manager):
        """
        Test that invalid status transition raises error.
        
        Validates: Requirements 6.2, 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_manager.update_status(job_id, JobStatus.FAILED)
    
    def test_invalid_transition_from_completed(self, job_manager):
        """
        Test that completed is a terminal state.
        
        Validates: Requirements 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        job_manager.update_status(job_id, JobStatus.COMPLETED)
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_manager.update_status(job_id, JobStatus.PROCESSING)
    
    def test_invalid_transition_from_failed(self, job_manager):
        """
        Test that failed is a terminal state.
        
        Validates: Requirements 6.3
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        job_manager.update_status(job_id, JobStatus.FAILED)
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_manager.update_status(job_id, JobStatus.PROCESSING)
    
    def test_update_status_nonexistent_job(self, job_manager):
        """
        Test that updating nonexistent job raises error.
        
        Validates: Requirements 6.2
        """
        with pytest.raises(ValueError, match="Job not found"):
            job_manager.update_status("nonexistent-job-id", JobStatus.PROCESSING)
    
    def test_get_job_returns_all_fields(self, job_manager):
        """
        Test that get_job returns all job fields.
        
        Validates: Requirements 6.5
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        job = job_manager.get_job(job_id)
        
        assert "job_id" in job
        assert "job_type" in job
        assert "video_id" in job
        assert "status" in job
        assert "progress" in job
        assert "result_path" in job
        assert "error_message" in job
        assert "created_at" in job
        assert "updated_at" in job
    
    def test_get_job_nonexistent_returns_none(self, job_manager):
        """
        Test that get_job returns None for nonexistent job.
        
        Validates: Requirements 6.5
        """
        job = job_manager.get_job("nonexistent-job-id")
        assert job is None
    
    def test_list_jobs_returns_all_jobs(self, job_manager):
        """
        Test that list_jobs returns all created jobs.
        
        Validates: Requirements 6.6
        """
        job_id_1 = job_manager.create_job("caption_generation", "video-1")
        job_id_2 = job_manager.create_job("video_processing", "video-2")
        job_id_3 = job_manager.create_job("watermark_application", "video-3")
        
        jobs = job_manager.list_jobs()
        
        assert len(jobs) == 3
        job_ids = [j["job_id"] for j in jobs]
        assert job_id_1 in job_ids
        assert job_id_2 in job_ids
        assert job_id_3 in job_ids
    
    def test_list_jobs_filter_by_video_id(self, job_manager):
        """
        Test that list_jobs can filter by video ID.
        
        Validates: Requirements 6.6
        """
        job_manager.create_job("caption_generation", "video-1")
        job_manager.create_job("video_processing", "video-1")
        job_manager.create_job("caption_generation", "video-2")
        
        jobs_video_1 = job_manager.list_jobs(video_id="video-1")
        jobs_video_2 = job_manager.list_jobs(video_id="video-2")
        
        assert len(jobs_video_1) == 2
        assert len(jobs_video_2) == 1
        
        for job in jobs_video_1:
            assert job["video_id"] == "video-1"
        
        for job in jobs_video_2:
            assert job["video_id"] == "video-2"
    
    def test_list_jobs_empty_returns_empty_list(self, job_manager):
        """
        Test that list_jobs returns empty list when no jobs exist.
        
        Validates: Requirements 6.6
        """
        jobs = job_manager.list_jobs()
        assert jobs == []
    
    def test_list_jobs_sorted_by_created_at(self, job_manager):
        """
        Test that list_jobs returns jobs sorted by created_at descending.
        
        Validates: Requirements 6.6
        """
        import time
        
        job_id_1 = job_manager.create_job("job1", "video-1")
        time.sleep(0.01)
        job_id_2 = job_manager.create_job("job2", "video-2")
        time.sleep(0.01)
        job_id_3 = job_manager.create_job("job3", "video-3")
        
        jobs = job_manager.list_jobs()
        
        # Should be sorted newest first
        assert jobs[0]["job_id"] == job_id_3
        assert jobs[1]["job_id"] == job_id_2
        assert jobs[2]["job_id"] == job_id_1
    
    def test_delete_job_removes_job(self, job_manager):
        """
        Test that delete_job removes the job from storage.
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        
        result = job_manager.delete_job(job_id)
        
        assert result is True
        assert job_manager.get_job(job_id) is None
    
    def test_delete_job_nonexistent_returns_false(self, job_manager):
        """
        Test that delete_job returns False for nonexistent job.
        """
        result = job_manager.delete_job("nonexistent-job-id")
        assert result is False
    
    def test_delete_job_removes_from_listing(self, job_manager):
        """
        Test that deleted job is removed from list_jobs results.
        """
        job_id_1 = job_manager.create_job("job1", "video-1")
        job_id_2 = job_manager.create_job("job2", "video-2")
        
        job_manager.delete_job(job_id_1)
        
        jobs = job_manager.list_jobs()
        job_ids = [j["job_id"] for j in jobs]
        
        assert job_id_1 not in job_ids
        assert job_id_2 in job_ids
    
    def test_delete_video_jobs_removes_all_video_jobs(self, job_manager):
        """
        Test that delete_video_jobs removes all jobs for a video.
        """
        job_manager.create_job("job1", "video-1")
        job_manager.create_job("job2", "video-1")
        job_manager.create_job("job3", "video-2")
        
        deleted_count = job_manager.delete_video_jobs("video-1")
        
        assert deleted_count == 2
        assert len(job_manager.list_jobs(video_id="video-1")) == 0
        assert len(job_manager.list_jobs(video_id="video-2")) == 1
    
    def test_idempotent_status_update(self, job_manager):
        """
        Test that updating to the same status is allowed (idempotent).
        """
        job_id = job_manager.create_job("caption_generation", "video-123")
        
        # Should not raise error
        job_manager.update_status(job_id, JobStatus.PENDING)
        
        job = job_manager.get_job(job_id)
        assert job["status"] == JobStatus.PENDING
