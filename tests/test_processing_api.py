"""
Tests for the video processing API endpoints.

Tests the POST /api/v1/videos/{video_id}/process and 
GET /api/v1/videos/{video_id}/output endpoints.

Validates: Requirements 4.5, 4.7, 5.3, 5.5, 5.6
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.processing import router
from app.api import videos, watermarks
from app.models.enums import JobStatus, WatermarkPosition


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_video_metadata():
    """Set up mock video metadata."""
    video_id = "test-video-123"
    videos.video_metadata_store[video_id] = {
        "video_id": video_id,
        "filename": "test_video.mp4",
        "stored_filename": f"{video_id}.mp4",
        "duration_seconds": 120.0,
        "resolution": "1920x1080",
        "file_size_bytes": 10000000,
        "has_captions": False,
        "has_output": False,
        "created_at": datetime.now(timezone.utc),
    }
    yield video_id
    # Cleanup
    if video_id in videos.video_metadata_store:
        del videos.video_metadata_store[video_id]


@pytest.fixture
def mock_watermark_metadata():
    """Set up mock watermark metadata."""
    watermark_id = "test-watermark-456"
    watermarks.watermark_metadata_store[watermark_id] = {
        "watermark_id": watermark_id,
        "filename": "logo.png",
        "stored_filename": f"{watermark_id}.png",
        "width": 200,
        "height": 100,
        "created_at": datetime.now(timezone.utc),
    }
    yield watermark_id
    # Cleanup
    if watermark_id in watermarks.watermark_metadata_store:
        del watermarks.watermark_metadata_store[watermark_id]


class TestProcessVideoEndpoint:
    """Tests for POST /api/v1/videos/{video_id}/process endpoint."""
    
    def test_process_video_not_found(self, client):
        """Test processing a non-existent video returns 404."""
        response = client.post(
            "/api/v1/videos/nonexistent-video/process",
            json={"apply_captions": True}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
    
    def test_process_video_no_operation_selected(self, client, mock_video_metadata):
        """Test processing without any operation returns 400."""
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={"apply_captions": False, "apply_watermark": False}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_PARAMETER"
        assert "at least one" in data["detail"]["message"].lower()
    
    @patch("app.api.processing.file_storage")
    def test_process_video_captions_not_found(self, mock_storage, client, mock_video_metadata):
        """Test processing with captions when captions don't exist returns 404."""
        # Mock video file exists but caption file doesn't
        mock_storage.get_file_path.side_effect = lambda filename, file_type: (
            f"/storage/uploads/{filename}" if file_type == "upload" else None
        )
        
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={"apply_captions": True}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "CAPTION_NOT_FOUND"
    
    def test_process_video_watermark_id_required(self, client, mock_video_metadata):
        """Test processing with watermark but no watermark_id returns 400."""
        with patch("app.api.processing.file_storage") as mock_storage:
            mock_storage.get_file_path.return_value = "/storage/uploads/test.mp4"
            
            response = client.post(
                f"/api/v1/videos/{mock_video_metadata}/process",
                json={"apply_watermark": True}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error_code"] == "INVALID_PARAMETER"
            assert "watermark_id" in data["detail"]["message"].lower()
    
    def test_process_video_watermark_not_found(self, client, mock_video_metadata):
        """Test processing with non-existent watermark returns 404."""
        with patch("app.api.processing.file_storage") as mock_storage:
            mock_storage.get_file_path.return_value = "/storage/uploads/test.mp4"
            
            response = client.post(
                f"/api/v1/videos/{mock_video_metadata}/process",
                json={
                    "apply_watermark": True,
                    "watermark_id": "nonexistent-watermark"
                }
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error_code"] == "WATERMARK_NOT_FOUND"
    
    @patch("app.api.processing.process_video_task")
    @patch("app.api.processing.job_manager")
    @patch("app.api.processing.file_storage")
    def test_process_video_with_captions_success(
        self, mock_storage, mock_job_manager, mock_task, client, mock_video_metadata
    ):
        """Test successful video processing with captions."""
        # Setup mocks
        mock_storage.get_file_path.side_effect = lambda filename, file_type: {
            "upload": f"/storage/uploads/{filename}",
            "caption": f"/storage/captions/{filename}" if "srt" in filename else None,
        }.get(file_type)
        
        job_id = "job-123"
        now = datetime.now(timezone.utc)
        mock_job_manager.create_job.return_value = job_id
        mock_job_manager.get_job.return_value = {
            "job_id": job_id,
            "job_type": "video_processing",
            "video_id": mock_video_metadata,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={"apply_captions": True}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["job_type"] == "video_processing"
        assert data["video_id"] == mock_video_metadata
        assert data["status"] == "pending"
        
        # Verify task was queued
        mock_task.delay.assert_called_once()
    
    @patch("app.api.processing.process_video_task")
    @patch("app.api.processing.job_manager")
    @patch("app.api.processing.file_storage")
    def test_process_video_with_watermark_success(
        self, mock_storage, mock_job_manager, mock_task, 
        client, mock_video_metadata, mock_watermark_metadata
    ):
        """Test successful video processing with watermark."""
        # Setup mocks
        mock_storage.get_file_path.side_effect = lambda filename, file_type: {
            "upload": f"/storage/uploads/{filename}",
            "watermark": f"/storage/watermarks/{filename}",
        }.get(file_type)
        
        job_id = "job-456"
        now = datetime.now(timezone.utc)
        mock_job_manager.create_job.return_value = job_id
        mock_job_manager.get_job.return_value = {
            "job_id": job_id,
            "job_type": "video_processing",
            "video_id": mock_video_metadata,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={
                "apply_watermark": True,
                "watermark_id": mock_watermark_metadata,
                "watermark_position": "top-left",
                "watermark_opacity": 0.8
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        
        # Verify task was queued with correct parameters
        mock_task.delay.assert_called_once()
        call_kwargs = mock_task.delay.call_args.kwargs
        assert call_kwargs["watermark_position"] == "top-left"
        assert call_kwargs["watermark_opacity"] == 0.8
    
    @patch("app.api.processing.process_video_task")
    @patch("app.api.processing.job_manager")
    @patch("app.api.processing.file_storage")
    def test_process_video_with_both_captions_and_watermark(
        self, mock_storage, mock_job_manager, mock_task,
        client, mock_video_metadata, mock_watermark_metadata
    ):
        """Test successful video processing with both captions and watermark."""
        # Setup mocks
        mock_storage.get_file_path.side_effect = lambda filename, file_type: {
            "upload": f"/storage/uploads/{filename}",
            "caption": f"/storage/captions/{filename}" if "srt" in filename else None,
            "watermark": f"/storage/watermarks/{filename}",
        }.get(file_type)
        
        job_id = "job-789"
        now = datetime.now(timezone.utc)
        mock_job_manager.create_job.return_value = job_id
        mock_job_manager.get_job.return_value = {
            "job_id": job_id,
            "job_type": "video_processing",
            "video_id": mock_video_metadata,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={
                "apply_captions": True,
                "apply_watermark": True,
                "watermark_id": mock_watermark_metadata,
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        
        # Verify task was queued with both caption and watermark paths
        mock_task.delay.assert_called_once()
        call_kwargs = mock_task.delay.call_args.kwargs
        assert call_kwargs["caption_path"] is not None
        assert call_kwargs["watermark_path"] is not None
    
    def test_process_video_default_watermark_settings(self, client, mock_video_metadata, mock_watermark_metadata):
        """Test that default watermark settings are applied."""
        with patch("app.api.processing.file_storage") as mock_storage, \
             patch("app.api.processing.job_manager") as mock_job_manager, \
             patch("app.api.processing.process_video_task") as mock_task:
            
            mock_storage.get_file_path.side_effect = lambda filename, file_type: {
                "upload": f"/storage/uploads/{filename}",
                "watermark": f"/storage/watermarks/{filename}",
            }.get(file_type)
            
            job_id = "job-default"
            now = datetime.now(timezone.utc)
            mock_job_manager.create_job.return_value = job_id
            mock_job_manager.get_job.return_value = {
                "job_id": job_id,
                "job_type": "video_processing",
                "video_id": mock_video_metadata,
                "status": JobStatus.PENDING,
                "progress": None,
                "result_path": None,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            }
            
            # Request with only required fields
            response = client.post(
                f"/api/v1/videos/{mock_video_metadata}/process",
                json={
                    "apply_watermark": True,
                    "watermark_id": mock_watermark_metadata,
                }
            )
            
            assert response.status_code == 202
            
            # Verify default values were used
            call_kwargs = mock_task.delay.call_args.kwargs
            assert call_kwargs["watermark_position"] == "bottom-right"  # Default
            assert call_kwargs["watermark_opacity"] == 0.5  # Default


class TestDownloadOutputEndpoint:
    """Tests for GET /api/v1/videos/{video_id}/output endpoint."""
    
    def test_download_output_video_not_found(self, client):
        """Test downloading output for non-existent video returns 404."""
        response = client.get("/api/v1/videos/nonexistent-video/output")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
    
    @patch("app.api.processing.file_storage")
    def test_download_output_not_processed(self, mock_storage, client, mock_video_metadata):
        """Test downloading output when video hasn't been processed returns 404."""
        mock_storage.get_file_path.return_value = None
        
        response = client.get(f"/api/v1/videos/{mock_video_metadata}/output")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "OUTPUT_NOT_FOUND"
    
    @patch("app.api.processing.file_storage")
    def test_download_output_success(self, mock_storage, client, mock_video_metadata, tmp_path):
        """Test successful output download."""
        # Create a temporary file to serve
        output_file = tmp_path / f"{mock_video_metadata}.mp4"
        output_file.write_bytes(b"fake video content")
        
        mock_storage.get_file_path.return_value = str(output_file)
        
        response = client.get(f"/api/v1/videos/{mock_video_metadata}/output")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"
        # Check filename in content-disposition header
        assert "test_video_processed.mp4" in response.headers.get("content-disposition", "")


class TestProcessVideoRequestValidation:
    """Tests for ProcessVideoRequest validation."""
    
    def test_opacity_validation_below_range(self, client, mock_video_metadata, mock_watermark_metadata):
        """Test that opacity below 0.0 is rejected."""
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={
                "apply_watermark": True,
                "watermark_id": mock_watermark_metadata,
                "watermark_opacity": -0.1
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_opacity_validation_above_range(self, client, mock_video_metadata, mock_watermark_metadata):
        """Test that opacity above 1.0 is rejected."""
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={
                "apply_watermark": True,
                "watermark_id": mock_watermark_metadata,
                "watermark_opacity": 1.5
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_watermark_position(self, client, mock_video_metadata, mock_watermark_metadata):
        """Test that invalid watermark position is rejected."""
        response = client.post(
            f"/api/v1/videos/{mock_video_metadata}/process",
            json={
                "apply_watermark": True,
                "watermark_id": mock_watermark_metadata,
                "watermark_position": "invalid-position"
            }
        )
        
        assert response.status_code == 422  # Validation error
