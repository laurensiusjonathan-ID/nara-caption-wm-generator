"""
Unit tests for video API endpoints.

Tests the video upload, metadata retrieval, and deletion endpoints
defined in app/api/videos.py.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.3
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
import io

from app.main import app
from app.api.videos import router, video_metadata_store, file_storage


# Create test client with the videos router
app.include_router(router, prefix="/api/v1", tags=["Videos"])
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_metadata_store():
    """Clear the video metadata store before each test."""
    video_metadata_store.clear()
    yield
    video_metadata_store.clear()


class TestVideoUpload:
    """Tests for POST /api/v1/videos/upload endpoint."""
    
    def test_upload_video_invalid_format_wmv(self):
        """
        Test that uploading an unsupported format returns 400.
        
        Validates: Requirements 1.2, 1.3
        """
        # Create a fake video file with unsupported format
        file_content = b"fake video content"
        files = {"file": ("test_video.wmv", io.BytesIO(file_content), "video/x-ms-wmv")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
        assert "wmv" in data["detail"]["details"]["provided_format"]
        assert "mp4" in data["detail"]["details"]["supported_formats"]
    
    def test_upload_video_invalid_format_mkv(self):
        """
        Test that uploading MKV format returns 400.
        
        Validates: Requirements 1.2, 1.3
        """
        file_content = b"fake video content"
        files = {"file": ("test_video.mkv", io.BytesIO(file_content), "video/x-matroska")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
    
    def test_upload_video_no_filename(self):
        """
        Test that uploading without filename returns error.
        
        Note: FastAPI returns 422 for validation errors when filename is empty,
        or 400 when our validation catches it. Both are acceptable error responses.
        
        Validates: Requirements 1.3
        """
        file_content = b"fake video content"
        files = {"file": ("", io.BytesIO(file_content), "video/mp4")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        # Accept either 400 (our validation) or 422 (FastAPI validation)
        assert response.status_code in [400, 422]
    
    @patch.object(file_storage, 'save_upload')
    @patch.object(file_storage, 'get_file_path')
    @patch('app.api.videos.extract_video_metadata')
    def test_upload_video_success_mp4(self, mock_extract, mock_get_path, mock_save):
        """
        Test successful MP4 video upload.
        
        Validates: Requirements 1.1, 1.2, 1.4
        """
        # Setup mocks
        mock_save.return_value = "abc123-uuid.mp4"
        mock_get_path.return_value = "/storage/uploads/abc123-uuid.mp4"
        mock_metadata = MagicMock()
        mock_metadata.duration_seconds = 120.5
        mock_metadata.resolution = "1920x1080"
        mock_metadata.file_size_bytes = 1024000
        mock_extract.return_value = mock_metadata
        
        file_content = b"fake video content"
        files = {"file": ("test_video.mp4", io.BytesIO(file_content), "video/mp4")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == "abc123-uuid"
        assert data["filename"] == "test_video.mp4"
        assert data["duration_seconds"] == 120.5
        assert data["resolution"] == "1920x1080"
        assert data["file_size_bytes"] == 1024000
        assert "created_at" in data
    
    @patch.object(file_storage, 'save_upload')
    @patch.object(file_storage, 'get_file_path')
    @patch('app.api.videos.extract_video_metadata')
    def test_upload_video_success_mov(self, mock_extract, mock_get_path, mock_save):
        """
        Test successful MOV video upload.
        
        Validates: Requirements 1.1, 1.2, 1.4
        """
        mock_save.return_value = "def456-uuid.mov"
        mock_get_path.return_value = "/storage/uploads/def456-uuid.mov"
        mock_metadata = MagicMock()
        mock_metadata.duration_seconds = 60.0
        mock_metadata.resolution = "1280x720"
        mock_metadata.file_size_bytes = 512000
        mock_extract.return_value = mock_metadata
        
        file_content = b"fake video content"
        files = {"file": ("test_video.MOV", io.BytesIO(file_content), "video/quicktime")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == "def456-uuid"
        assert data["filename"] == "test_video.MOV"
    
    @patch.object(file_storage, 'save_upload')
    @patch.object(file_storage, 'get_file_path')
    @patch('app.api.videos.extract_video_metadata')
    def test_upload_video_success_avi(self, mock_extract, mock_get_path, mock_save):
        """
        Test successful AVI video upload.
        
        Validates: Requirements 1.1, 1.2, 1.4
        """
        mock_save.return_value = "ghi789-uuid.avi"
        mock_get_path.return_value = "/storage/uploads/ghi789-uuid.avi"
        mock_metadata = MagicMock()
        mock_metadata.duration_seconds = 300.0
        mock_metadata.resolution = "640x480"
        mock_metadata.file_size_bytes = 2048000
        mock_extract.return_value = mock_metadata
        
        file_content = b"fake video content"
        files = {"file": ("test_video.avi", io.BytesIO(file_content), "video/x-msvideo")}
        
        response = client.post("/api/v1/videos/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == "ghi789-uuid"


class TestGetVideo:
    """Tests for GET /api/v1/videos/{video_id} endpoint."""
    
    def test_get_video_not_found(self):
        """
        Test that requesting non-existent video returns 404.
        
        Validates: Requirements 1.6
        """
        response = client.get("/api/v1/videos/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
        assert "nonexistent-id" in data["detail"]["message"]
    
    @patch.object(file_storage, 'get_file_path')
    def test_get_video_success(self, mock_get_path):
        """
        Test successful video metadata retrieval.
        
        Validates: Requirements 1.5
        """
        # Setup: Add video to metadata store
        video_id = "test-video-123"
        created_at = datetime.utcnow()
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": "original_video.mp4",
            "stored_filename": f"{video_id}.mp4",
            "duration_seconds": 180.0,
            "resolution": "1920x1080",
            "file_size_bytes": 5000000,
            "has_captions": False,
            "has_output": False,
            "created_at": created_at,
        }
        
        # Mock file path checks (no captions or output)
        mock_get_path.return_value = None
        
        response = client.get(f"/api/v1/videos/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["filename"] == "original_video.mp4"
        assert data["duration_seconds"] == 180.0
        assert data["resolution"] == "1920x1080"
        assert data["file_size_bytes"] == 5000000
        assert data["has_captions"] is False
        assert data["has_output"] is False
    
    @patch.object(file_storage, 'get_file_path')
    def test_get_video_with_captions(self, mock_get_path):
        """
        Test video metadata shows has_captions=True when captions exist.
        
        Validates: Requirements 1.5
        """
        video_id = "video-with-captions"
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": "video.mp4",
            "stored_filename": f"{video_id}.mp4",
            "duration_seconds": 60.0,
            "resolution": "1280x720",
            "file_size_bytes": 1000000,
            "has_captions": False,
            "has_output": False,
            "created_at": datetime.utcnow(),
        }
        
        # Mock: caption file exists
        def get_path_side_effect(filename, file_type):
            if file_type == "caption" and filename.endswith(".srt"):
                return f"/storage/captions/{filename}"
            return None
        
        mock_get_path.side_effect = get_path_side_effect
        
        response = client.get(f"/api/v1/videos/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_captions"] is True
        assert data["has_output"] is False
    
    @patch.object(file_storage, 'get_file_path')
    def test_get_video_with_output(self, mock_get_path):
        """
        Test video metadata shows has_output=True when output exists.
        
        Validates: Requirements 1.5
        """
        video_id = "video-with-output"
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": "video.mp4",
            "stored_filename": f"{video_id}.mp4",
            "duration_seconds": 60.0,
            "resolution": "1280x720",
            "file_size_bytes": 1000000,
            "has_captions": False,
            "has_output": False,
            "created_at": datetime.utcnow(),
        }
        
        # Mock: output file exists
        def get_path_side_effect(filename, file_type):
            if file_type == "output":
                return f"/storage/outputs/{filename}"
            return None
        
        mock_get_path.side_effect = get_path_side_effect
        
        response = client.get(f"/api/v1/videos/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_captions"] is False
        assert data["has_output"] is True


class TestDeleteVideo:
    """Tests for DELETE /api/v1/videos/{video_id} endpoint."""
    
    def test_delete_video_not_found(self):
        """
        Test that deleting non-existent video returns 404.
        
        Validates: Requirements 1.6
        """
        response = client.delete("/api/v1/videos/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "VIDEO_NOT_FOUND"
    
    @patch.object(file_storage, 'delete_video_files')
    def test_delete_video_success(self, mock_delete):
        """
        Test successful video deletion.
        
        Validates: Requirements 8.3
        """
        video_id = "video-to-delete"
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": "video.mp4",
            "stored_filename": f"{video_id}.mp4",
            "duration_seconds": 60.0,
            "resolution": "1280x720",
            "file_size_bytes": 1000000,
            "has_captions": False,
            "has_output": False,
            "created_at": datetime.utcnow(),
        }
        
        response = client.delete(f"/api/v1/videos/{video_id}")
        
        assert response.status_code == 204
        assert video_id not in video_metadata_store
        mock_delete.assert_called_once_with(video_id)
    
    @patch.object(file_storage, 'delete_video_files')
    def test_delete_video_cascade_deletion(self, mock_delete):
        """
        Test that deletion triggers cascade file deletion.
        
        Validates: Requirements 8.3
        """
        video_id = "video-cascade-delete"
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": "video.mp4",
            "stored_filename": f"{video_id}.mp4",
            "duration_seconds": 120.0,
            "resolution": "1920x1080",
            "file_size_bytes": 2000000,
            "has_captions": True,
            "has_output": True,
            "created_at": datetime.utcnow(),
        }
        
        response = client.delete(f"/api/v1/videos/{video_id}")
        
        assert response.status_code == 204
        # Verify cascade deletion was called
        mock_delete.assert_called_once_with(video_id)
        # Verify metadata was removed
        assert video_id not in video_metadata_store
