"""
Unit tests for caption API endpoints.

Tests the caption generation, retrieval, and update endpoints
defined in app/api/captions.py.

Validates: Requirements 2.6, 2.7, 3.1, 3.2, 3.3, 3.4
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import tempfile
import os

from app.main import app
from app.api.captions import router, file_storage, job_manager
from app.api.videos import video_metadata_store
from app.models.enums import CaptionFormat, JobStatus


# Create test client with the captions router
app.include_router(router, prefix="/api/v1", tags=["Captions"])
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_metadata_store():
    """Clear the video metadata store before each test."""
    video_metadata_store.clear()
    yield
    video_metadata_store.clear()


@pytest.fixture
def sample_video_in_store():
    """Add a sample video to the metadata store."""
    video_id = "test-video-123"
    video_metadata_store[video_id] = {
        "video_id": video_id,
        "filename": "test_video.mp4",
        "stored_filename": f"{video_id}.mp4",
        "duration_seconds": 120.0,
        "resolution": "1920x1080",
        "file_size_bytes": 5000000,
        "has_captions": False,
        "has_output": False,
        "created_at": datetime.utcnow(),
    }
    return video_id


# Sample SRT content for testing
SAMPLE_SRT_CONTENT = """1
00:00:00,000 --> 00:00:02,500
Hello world

2
00:00:02,500 --> 00:00:05,000
This is a test
"""

# Sample VTT content for testing
SAMPLE_VTT_CONTENT = """WEBVTT

00:00:00.000 --> 00:00:02.500
Hello world

00:00:02.500 --> 00:00:05.000
This is a test
"""


class TestGenerateCaptions:
    """Tests for POST /api/v1/videos/{video_id}/captions/generate endpoint."""
    
    def test_generate_captions_video_not_found(self):
        """
        Test that generating captions for non-existent video returns 404.
        
        Validates: Requirements 2.6
        """
        response = client.post("/api/v1/videos/nonexistent-id/captions/generate")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
        assert "nonexistent-id" in data["detail"]["message"]
    
    @patch.object(file_storage, 'get_file_path')
    @patch.object(job_manager, 'create_job')
    @patch.object(job_manager, 'get_job')
    @patch('app.api.captions.generate_captions_task')
    def test_generate_captions_success(
        self, mock_task, mock_get_job, mock_create_job, mock_get_path, sample_video_in_store
    ):
        """
        Test successful caption generation job creation.
        
        Validates: Requirements 2.6, 2.7
        """
        video_id = sample_video_in_store
        job_id = "job-123"
        now = datetime.now(timezone.utc)
        
        # Setup mocks
        mock_get_path.return_value = f"/storage/uploads/{video_id}.mp4"
        mock_create_job.return_value = job_id
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "caption_generation",
            "video_id": video_id,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        mock_task.delay = MagicMock()
        
        response = client.post(f"/api/v1/videos/{video_id}/captions/generate")
        
        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["job_type"] == "caption_generation"
        assert data["video_id"] == video_id
        assert data["status"] == "pending"
        
        # Verify task was queued
        mock_task.delay.assert_called_once()
    
    @patch.object(file_storage, 'get_file_path')
    @patch.object(job_manager, 'create_job')
    @patch.object(job_manager, 'get_job')
    @patch('app.api.captions.generate_captions_task')
    def test_generate_captions_with_language(
        self, mock_task, mock_get_job, mock_create_job, mock_get_path, sample_video_in_store
    ):
        """
        Test caption generation with custom language.
        
        Validates: Requirements 2.6, 2.7
        """
        video_id = sample_video_in_store
        job_id = "job-456"
        now = datetime.now(timezone.utc)
        
        mock_get_path.return_value = f"/storage/uploads/{video_id}.mp4"
        mock_create_job.return_value = job_id
        mock_get_job.return_value = {
            "job_id": job_id,
            "job_type": "caption_generation",
            "video_id": video_id,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        mock_task.delay = MagicMock()
        
        response = client.post(
            f"/api/v1/videos/{video_id}/captions/generate",
            json={"language": "en", "output_format": "vtt"}
        )
        
        assert response.status_code == 202
        
        # Verify task was called with correct parameters
        call_kwargs = mock_task.delay.call_args.kwargs
        assert call_kwargs["language"] == "en"
        assert call_kwargs["output_format"] == "vtt"
    
    @patch.object(file_storage, 'get_file_path')
    def test_generate_captions_video_file_not_found(self, mock_get_path, sample_video_in_store):
        """
        Test that missing video file returns 500.
        
        Validates: Requirements 2.6
        """
        video_id = sample_video_in_store
        mock_get_path.return_value = None  # File not found
        
        response = client.post(f"/api/v1/videos/{video_id}/captions/generate")
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error_code"] == "INTERNAL_ERROR"


class TestGetCaptions:
    """Tests for GET /api/v1/videos/{video_id}/captions endpoint."""
    
    def test_get_captions_video_not_found(self):
        """
        Test that getting captions for non-existent video returns 404.
        
        Validates: Requirements 3.1
        """
        response = client.get("/api/v1/videos/nonexistent-id/captions")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
    
    @patch.object(file_storage, 'get_file_path')
    def test_get_captions_not_generated(self, mock_get_path, sample_video_in_store):
        """
        Test that getting captions when none exist returns 404.
        
        Validates: Requirements 3.1
        """
        video_id = sample_video_in_store
        mock_get_path.return_value = None  # No caption file
        
        response = client.get(f"/api/v1/videos/{video_id}/captions")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "CAPTION_NOT_FOUND"
    
    def test_get_captions_success_srt(self, sample_video_in_store):
        """
        Test successful caption retrieval in SRT format.
        
        Validates: Requirements 3.1, 3.2
        """
        video_id = sample_video_in_store
        
        # Create a temporary caption file
        with tempfile.TemporaryDirectory() as tmpdir:
            caption_path = os.path.join(tmpdir, f"{video_id}.srt")
            with open(caption_path, 'w') as f:
                f.write(SAMPLE_SRT_CONTENT)
            
            with patch.object(file_storage, 'get_file_path') as mock_get_path:
                def get_path_side_effect(filename, file_type):
                    if file_type == "caption" and filename.endswith(".srt"):
                        return caption_path
                    return None
                
                mock_get_path.side_effect = get_path_side_effect
                
                response = client.get(f"/api/v1/videos/{video_id}/captions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["format"] == "srt"
        assert len(data["segments"]) == 2
        assert data["segments"][0]["text"] == "Hello world"
        assert data["segments"][1]["text"] == "This is a test"
    
    def test_get_captions_success_vtt(self, sample_video_in_store):
        """
        Test successful caption retrieval in VTT format.
        
        Validates: Requirements 3.1, 3.2
        """
        video_id = sample_video_in_store
        
        with tempfile.TemporaryDirectory() as tmpdir:
            caption_path = os.path.join(tmpdir, f"{video_id}.vtt")
            with open(caption_path, 'w') as f:
                f.write(SAMPLE_VTT_CONTENT)
            
            with patch.object(file_storage, 'get_file_path') as mock_get_path:
                def get_path_side_effect(filename, file_type):
                    if file_type == "caption" and filename.endswith(".vtt"):
                        return caption_path
                    return None
                
                mock_get_path.side_effect = get_path_side_effect
                
                response = client.get(f"/api/v1/videos/{video_id}/captions?format=vtt")
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "vtt"
        assert len(data["segments"]) == 2
    
    def test_get_captions_format_conversion(self, sample_video_in_store):
        """
        Test caption format conversion (SRT to VTT).
        
        Validates: Requirements 3.1, 3.2
        """
        video_id = sample_video_in_store
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only SRT file exists
            srt_path = os.path.join(tmpdir, f"{video_id}.srt")
            with open(srt_path, 'w') as f:
                f.write(SAMPLE_SRT_CONTENT)
            
            with patch.object(file_storage, 'get_file_path') as mock_get_path:
                def get_path_side_effect(filename, file_type):
                    if file_type == "caption" and filename.endswith(".srt"):
                        return srt_path
                    return None
                
                mock_get_path.side_effect = get_path_side_effect
                
                # Request VTT format
                response = client.get(f"/api/v1/videos/{video_id}/captions?format=vtt")
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "vtt"
        assert "WEBVTT" in data["content"]


class TestUpdateCaptions:
    """Tests for PUT /api/v1/videos/{video_id}/captions endpoint."""
    
    def test_update_captions_video_not_found(self):
        """
        Test that updating captions for non-existent video returns 404.
        
        Validates: Requirements 3.3
        """
        response = client.put(
            "/api/v1/videos/nonexistent-id/captions",
            json={"format": "srt", "content": SAMPLE_SRT_CONTENT}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
    
    def test_update_captions_invalid_format(self, sample_video_in_store):
        """
        Test that invalid caption format returns 400.
        
        Validates: Requirements 3.4
        """
        video_id = sample_video_in_store
        
        response = client.put(
            f"/api/v1/videos/{video_id}/captions",
            json={"format": "srt", "content": "invalid caption content"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
    
    @patch.object(file_storage, 'save_caption')
    def test_update_captions_success_srt(self, mock_save, sample_video_in_store):
        """
        Test successful caption update with SRT format.
        
        Validates: Requirements 3.3
        """
        video_id = sample_video_in_store
        mock_save.return_value = f"{video_id}.srt"
        
        response = client.put(
            f"/api/v1/videos/{video_id}/captions",
            json={"format": "srt", "content": SAMPLE_SRT_CONTENT}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["format"] == "srt"
        assert len(data["segments"]) == 2
        
        # Verify save was called
        mock_save.assert_called_once_with(
            content=SAMPLE_SRT_CONTENT,
            video_id=video_id,
            format=CaptionFormat.SRT
        )
    
    @patch.object(file_storage, 'save_caption')
    def test_update_captions_success_vtt(self, mock_save, sample_video_in_store):
        """
        Test successful caption update with VTT format.
        
        Validates: Requirements 3.3
        """
        video_id = sample_video_in_store
        mock_save.return_value = f"{video_id}.vtt"
        
        response = client.put(
            f"/api/v1/videos/{video_id}/captions",
            json={"format": "vtt", "content": SAMPLE_VTT_CONTENT}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "vtt"
        assert len(data["segments"]) == 2
    
    def test_update_captions_invalid_timestamps(self, sample_video_in_store):
        """
        Test that captions with invalid timestamps return 400.
        
        Validates: Requirements 3.4
        """
        video_id = sample_video_in_store
        
        # Invalid: end time before start time
        invalid_srt = """1
00:00:05,000 --> 00:00:02,000
Invalid timestamps
"""
        
        response = client.put(
            f"/api/v1/videos/{video_id}/captions",
            json={"format": "srt", "content": invalid_srt}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
    
    def test_update_captions_missing_content(self, sample_video_in_store):
        """
        Test that missing content returns validation error.
        
        Validates: Requirements 3.4
        """
        video_id = sample_video_in_store
        
        response = client.put(
            f"/api/v1/videos/{video_id}/captions",
            json={"format": "srt"}  # Missing content
        )
        
        assert response.status_code == 422  # Validation error
