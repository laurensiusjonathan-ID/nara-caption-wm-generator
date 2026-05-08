"""
Unit tests for job API endpoints.

Tests the job status retrieval and job listing endpoints
defined in app/api/jobs.py.

Validates: Requirements 6.5, 6.6
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.main import app
from app.api.jobs import router, job_manager
from app.models.enums import JobStatus


# Create test client with the jobs router
app.include_router(router, prefix="/api/v1", tags=["Jobs"])
client = TestClient(app)


class TestGetJob:
    """Tests for GET /api/v1/jobs/{job_id} endpoint."""
    
    @patch.object(job_manager, 'get_job')
    def test_get_job_not_found(self, mock_get_job):
        """
        Test that requesting non-existent job returns 404.
        
        Validates: Requirements 6.5
        """
        mock_get_job.return_value = None
        
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "JOB_NOT_FOUND"
        assert "nonexistent-job-id" in data["detail"]["message"]
    
    @patch.object(job_manager, 'get_job')
    def test_get_job_pending_status(self, mock_get_job):
        """
        Test successful retrieval of a pending job.
        
        Validates: Requirements 6.5
        """
        job_id = "test-job-123"
        created_at = datetime.now(timezone.utc)
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "caption_generation",
            "video_id": "video-456",
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
        
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["job_type"] == "caption_generation"
        assert data["video_id"] == "video-456"
        assert data["status"] == "pending"
        assert data["progress"] is None
        assert data["result_path"] is None
        assert data["error_message"] is None
    
    @patch.object(job_manager, 'get_job')
    def test_get_job_processing_with_progress(self, mock_get_job):
        """
        Test retrieval of a processing job with progress.
        
        Validates: Requirements 6.5
        """
        job_id = "processing-job-789"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "video_processing",
            "video_id": "video-abc",
            "status": JobStatus.PROCESSING,
            "progress": 45,
            "result_path": None,
            "error_message": None,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["progress"] == 45
    
    @patch.object(job_manager, 'get_job')
    def test_get_job_completed_with_result(self, mock_get_job):
        """
        Test retrieval of a completed job with result path.
        
        Validates: Requirements 6.5
        """
        job_id = "completed-job-xyz"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "caption_generation",
            "video_id": "video-def",
            "status": JobStatus.COMPLETED,
            "progress": 100,
            "result_path": "/storage/captions/video-def.srt",
            "error_message": None,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result_path"] == "/storage/captions/video-def.srt"
        assert data["error_message"] is None
    
    @patch.object(job_manager, 'get_job')
    def test_get_job_failed_with_error(self, mock_get_job):
        """
        Test retrieval of a failed job with error message.
        
        Validates: Requirements 6.5
        """
        job_id = "failed-job-err"
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "video_processing",
            "video_id": "video-ghi",
            "status": JobStatus.FAILED,
            "progress": 30,
            "result_path": None,
            "error_message": "FFmpeg processing failed: Invalid video codec",
            "created_at": created_at,
            "updated_at": updated_at,
        }
        
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "failed"
        assert data["error_message"] == "FFmpeg processing failed: Invalid video codec"
        assert data["result_path"] is None


class TestListJobs:
    """Tests for GET /api/v1/jobs endpoint."""
    
    @patch.object(job_manager, 'list_jobs')
    def test_list_jobs_empty(self, mock_list_jobs):
        """
        Test listing jobs when no jobs exist.
        
        Validates: Requirements 6.6
        """
        mock_list_jobs.return_value = []
        
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
    
    @patch.object(job_manager, 'list_jobs')
    def test_list_jobs_multiple(self, mock_list_jobs):
        """
        Test listing multiple jobs.
        
        Validates: Requirements 6.6
        """
        now = datetime.now(timezone.utc)
        mock_list_jobs.return_value = [
            {
                "job_id": "job-1",
                "job_type": "caption_generation",
                "video_id": "video-1",
                "status": JobStatus.COMPLETED,
                "progress": 100,
                "result_path": "/storage/captions/video-1.srt",
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "job_id": "job-2",
                "job_type": "video_processing",
                "video_id": "video-2",
                "status": JobStatus.PROCESSING,
                "progress": 50,
                "result_path": None,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "job_id": "job-3",
                "job_type": "caption_generation",
                "video_id": "video-3",
                "status": JobStatus.PENDING,
                "progress": None,
                "result_path": None,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            },
        ]
        
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 3
        assert data["total"] == 3
        
        # Verify job data
        assert data["jobs"][0]["job_id"] == "job-1"
        assert data["jobs"][0]["status"] == "completed"
        assert data["jobs"][1]["job_id"] == "job-2"
        assert data["jobs"][1]["status"] == "processing"
        assert data["jobs"][2]["job_id"] == "job-3"
        assert data["jobs"][2]["status"] == "pending"
    
    @patch.object(job_manager, 'list_jobs')
    def test_list_jobs_filter_by_video_id(self, mock_list_jobs):
        """
        Test listing jobs filtered by video_id.
        
        Validates: Requirements 6.6
        """
        now = datetime.now(timezone.utc)
        mock_list_jobs.return_value = [
            {
                "job_id": "job-for-video-x",
                "job_type": "caption_generation",
                "video_id": "video-x",
                "status": JobStatus.COMPLETED,
                "progress": 100,
                "result_path": "/storage/captions/video-x.srt",
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            },
        ]
        
        response = client.get("/api/v1/jobs?video_id=video-x")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["total"] == 1
        assert data["jobs"][0]["video_id"] == "video-x"
        
        # Verify the mock was called with the video_id filter
        mock_list_jobs.assert_called_once_with(video_id="video-x")
    
    @patch.object(job_manager, 'list_jobs')
    def test_list_jobs_filter_no_results(self, mock_list_jobs):
        """
        Test listing jobs with filter that returns no results.
        
        Validates: Requirements 6.6
        """
        mock_list_jobs.return_value = []
        
        response = client.get("/api/v1/jobs?video_id=nonexistent-video")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
        mock_list_jobs.assert_called_once_with(video_id="nonexistent-video")
    
    @patch.object(job_manager, 'list_jobs')
    def test_list_jobs_response_structure(self, mock_list_jobs):
        """
        Test that job list response has correct structure.
        
        Validates: Requirements 6.6
        """
        now = datetime.now(timezone.utc)
        mock_list_jobs.return_value = [
            {
                "job_id": "struct-test-job",
                "job_type": "video_processing",
                "video_id": "struct-video",
                "status": JobStatus.FAILED,
                "progress": 25,
                "result_path": None,
                "error_message": "Test error",
                "created_at": now,
                "updated_at": now,
            },
        ]
        
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total"], int)
        
        # Verify job structure
        job = data["jobs"][0]
        assert "job_id" in job
        assert "job_type" in job
        assert "video_id" in job
        assert "status" in job
        assert "progress" in job
        assert "result_path" in job
        assert "error_message" in job
        assert "created_at" in job
        assert "updated_at" in job
