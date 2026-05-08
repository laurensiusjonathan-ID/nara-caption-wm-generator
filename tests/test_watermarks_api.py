"""
Unit tests for watermark API endpoints.

Tests the watermark upload, metadata retrieval, and deletion endpoints
defined in app/api/watermarks.py.

Validates: Requirements 4.1, 4.2
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
import io

from app.main import app
from app.api.watermarks import router, watermark_metadata_store, file_storage


# Create test client with the watermarks router
app.include_router(router, prefix="/api/v1", tags=["Watermarks"])
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_metadata_store():
    """Clear the watermark metadata store before each test."""
    watermark_metadata_store.clear()
    yield
    watermark_metadata_store.clear()


class TestWatermarkUpload:
    """Tests for POST /api/v1/watermarks/upload endpoint."""
    
    def test_upload_watermark_invalid_format_jpg(self):
        """
        Test that uploading a JPG file returns 400.
        
        Validates: Requirements 4.1, 4.2
        """
        file_content = b"fake image content"
        files = {"file": ("watermark.jpg", io.BytesIO(file_content), "image/jpeg")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
        assert "jpg" in data["detail"]["details"]["provided_format"]
        assert "png" in data["detail"]["details"]["supported_formats"]
    
    def test_upload_watermark_invalid_format_gif(self):
        """
        Test that uploading a GIF file returns 400.
        
        Validates: Requirements 4.1, 4.2
        """
        file_content = b"fake image content"
        files = {"file": ("watermark.gif", io.BytesIO(file_content), "image/gif")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
    
    def test_upload_watermark_invalid_format_bmp(self):
        """
        Test that uploading a BMP file returns 400.
        
        Validates: Requirements 4.1, 4.2
        """
        file_content = b"fake image content"
        files = {"file": ("watermark.bmp", io.BytesIO(file_content), "image/bmp")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_FORMAT"
    
    def test_upload_watermark_no_filename(self):
        """
        Test that uploading without filename returns error.
        
        Validates: Requirements 4.2
        """
        file_content = b"fake image content"
        files = {"file": ("", io.BytesIO(file_content), "image/png")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        # Accept either 400 (our validation) or 422 (FastAPI validation)
        assert response.status_code in [400, 422]
    
    @patch.object(file_storage, 'save_watermark')
    @patch.object(file_storage, 'get_file_path')
    @patch('app.api.watermarks.validate_watermark_file')
    def test_upload_watermark_success_png(self, mock_validate, mock_get_path, mock_save):
        """
        Test successful PNG watermark upload.
        
        Validates: Requirements 4.1
        """
        # Setup mocks
        mock_save.return_value = "abc123-uuid.png"
        mock_get_path.return_value = "/storage/watermarks/abc123-uuid.png"
        mock_metadata = MagicMock()
        mock_metadata.width = 200
        mock_metadata.height = 100
        mock_metadata.has_alpha = True
        mock_validate.return_value = mock_metadata
        
        file_content = b"fake png content"
        files = {"file": ("logo.png", io.BytesIO(file_content), "image/png")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["watermark_id"] == "abc123-uuid"
        assert data["filename"] == "logo.png"
        assert data["width"] == 200
        assert data["height"] == 100
        assert "created_at" in data
    
    @patch.object(file_storage, 'save_watermark')
    @patch.object(file_storage, 'get_file_path')
    @patch('app.api.watermarks.validate_watermark_file')
    def test_upload_watermark_success_uppercase_png(self, mock_validate, mock_get_path, mock_save):
        """
        Test successful PNG watermark upload with uppercase extension.
        
        Validates: Requirements 4.1
        """
        mock_save.return_value = "def456-uuid.PNG"
        mock_get_path.return_value = "/storage/watermarks/def456-uuid.PNG"
        mock_metadata = MagicMock()
        mock_metadata.width = 300
        mock_metadata.height = 150
        mock_metadata.has_alpha = True
        mock_validate.return_value = mock_metadata
        
        file_content = b"fake png content"
        files = {"file": ("LOGO.PNG", io.BytesIO(file_content), "image/png")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["watermark_id"] == "def456-uuid"
        assert data["filename"] == "LOGO.PNG"
    
    @patch.object(file_storage, 'save_watermark')
    @patch.object(file_storage, 'get_file_path')
    def test_upload_watermark_storage_failure(self, mock_get_path, mock_save):
        """
        Test that storage failure returns 500.
        
        Validates: Requirements 4.1
        """
        mock_save.return_value = "abc123-uuid.png"
        mock_get_path.return_value = None  # Simulate storage failure
        
        file_content = b"fake png content"
        files = {"file": ("logo.png", io.BytesIO(file_content), "image/png")}
        
        response = client.post("/api/v1/watermarks/upload", files=files)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error_code"] == "INTERNAL_ERROR"


class TestGetWatermark:
    """Tests for GET /api/v1/watermarks/{watermark_id} endpoint."""
    
    def test_get_watermark_not_found(self):
        """
        Test that requesting non-existent watermark returns 404.
        
        Validates: Requirements 4.1
        """
        response = client.get("/api/v1/watermarks/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "WATERMARK_NOT_FOUND"
        assert "nonexistent-id" in data["detail"]["message"]
    
    def test_get_watermark_success(self):
        """
        Test successful watermark metadata retrieval.
        
        Validates: Requirements 4.1
        """
        # Setup: Add watermark to metadata store
        watermark_id = "test-watermark-123"
        created_at = datetime.utcnow()
        watermark_metadata_store[watermark_id] = {
            "watermark_id": watermark_id,
            "filename": "company_logo.png",
            "stored_filename": f"{watermark_id}.png",
            "width": 250,
            "height": 125,
            "created_at": created_at,
        }
        
        response = client.get(f"/api/v1/watermarks/{watermark_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["watermark_id"] == watermark_id
        assert data["filename"] == "company_logo.png"
        assert data["width"] == 250
        assert data["height"] == 125
        assert "created_at" in data
    
    def test_get_watermark_multiple_watermarks(self):
        """
        Test retrieving specific watermark when multiple exist.
        
        Validates: Requirements 4.1
        """
        # Setup: Add multiple watermarks
        watermark_id_1 = "watermark-1"
        watermark_id_2 = "watermark-2"
        
        watermark_metadata_store[watermark_id_1] = {
            "watermark_id": watermark_id_1,
            "filename": "logo1.png",
            "stored_filename": f"{watermark_id_1}.png",
            "width": 100,
            "height": 50,
            "created_at": datetime.utcnow(),
        }
        watermark_metadata_store[watermark_id_2] = {
            "watermark_id": watermark_id_2,
            "filename": "logo2.png",
            "stored_filename": f"{watermark_id_2}.png",
            "width": 200,
            "height": 100,
            "created_at": datetime.utcnow(),
        }
        
        response = client.get(f"/api/v1/watermarks/{watermark_id_2}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["watermark_id"] == watermark_id_2
        assert data["filename"] == "logo2.png"
        assert data["width"] == 200


class TestDeleteWatermark:
    """Tests for DELETE /api/v1/watermarks/{watermark_id} endpoint."""
    
    def test_delete_watermark_not_found(self):
        """
        Test that deleting non-existent watermark returns 404.
        
        Validates: Requirements 4.1
        """
        response = client.delete("/api/v1/watermarks/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "WATERMARK_NOT_FOUND"
    
    @patch.object(file_storage, 'get_file_path')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_watermark_success(self, mock_remove, mock_exists, mock_get_path):
        """
        Test successful watermark deletion.
        
        Validates: Requirements 4.1
        """
        watermark_id = "watermark-to-delete"
        watermark_metadata_store[watermark_id] = {
            "watermark_id": watermark_id,
            "filename": "logo.png",
            "stored_filename": f"{watermark_id}.png",
            "width": 150,
            "height": 75,
            "created_at": datetime.utcnow(),
        }
        
        mock_get_path.return_value = f"/storage/watermarks/{watermark_id}.png"
        mock_exists.return_value = True
        
        response = client.delete(f"/api/v1/watermarks/{watermark_id}")
        
        assert response.status_code == 204
        assert watermark_id not in watermark_metadata_store
        mock_remove.assert_called_once()
    
    @patch.object(file_storage, 'get_file_path')
    def test_delete_watermark_file_not_on_disk(self, mock_get_path):
        """
        Test deletion succeeds even if file is not on disk.
        
        Validates: Requirements 4.1
        """
        watermark_id = "watermark-no-file"
        watermark_metadata_store[watermark_id] = {
            "watermark_id": watermark_id,
            "filename": "logo.png",
            "stored_filename": f"{watermark_id}.png",
            "width": 150,
            "height": 75,
            "created_at": datetime.utcnow(),
        }
        
        mock_get_path.return_value = None  # File not found
        
        response = client.delete(f"/api/v1/watermarks/{watermark_id}")
        
        assert response.status_code == 204
        assert watermark_id not in watermark_metadata_store
    
    @patch.object(file_storage, 'get_file_path')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_watermark_removes_from_store(self, mock_remove, mock_exists, mock_get_path):
        """
        Test that deletion removes watermark from metadata store.
        
        Validates: Requirements 4.1
        """
        watermark_id = "watermark-store-test"
        watermark_metadata_store[watermark_id] = {
            "watermark_id": watermark_id,
            "filename": "logo.png",
            "stored_filename": f"{watermark_id}.png",
            "width": 100,
            "height": 50,
            "created_at": datetime.utcnow(),
        }
        
        mock_get_path.return_value = f"/storage/watermarks/{watermark_id}.png"
        mock_exists.return_value = True
        
        # Verify watermark exists before deletion
        assert watermark_id in watermark_metadata_store
        
        response = client.delete(f"/api/v1/watermarks/{watermark_id}")
        
        assert response.status_code == 204
        # Verify watermark is removed from store
        assert watermark_id not in watermark_metadata_store
