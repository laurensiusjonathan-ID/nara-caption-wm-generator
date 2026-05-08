"""
Tests for the exception handlers module.

This module tests:
- Custom exception classes for each error category
- FastAPI exception handlers for consistent error responses
- Validation error handling with field-level details
- Generic exception handling without exposing internal details

Validates: Requirements 1.3, 1.6, 2.8, 3.4, 4.2, 7.3, 7.4, 7.5
"""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.exceptions import (
    # Exception classes
    APIException,
    VideoNotFoundError,
    WatermarkNotFoundError,
    JobNotFoundError,
    CaptionNotFoundError,
    InvalidFormatError,
    InvalidParameterError,
    ProcessingError,
    AudioExtractionError,
    TranscriptionError,
    FFmpegError,
    InternalError,
    ServiceUnavailableError,
    # Handler registration
    register_exception_handlers,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_app():
    """Create a test FastAPI app with exception handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the test app."""
    return TestClient(test_app, raise_server_exceptions=False)


# ============================================================================
# Test Custom Exception Classes
# ============================================================================

class TestVideoNotFoundError:
    """Tests for VideoNotFoundError exception."""
    
    def test_creates_with_video_id(self):
        """Test exception is created with correct attributes."""
        exc = VideoNotFoundError("test-video-123")
        
        assert exc.error_code == "VIDEO_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "test-video-123" in exc.message
        assert exc.video_id == "test-video-123"
    
    def test_with_details(self):
        """Test exception with additional details."""
        details = {"additional_info": "some context"}
        exc = VideoNotFoundError("vid-456", details=details)
        
        assert exc.details == details


class TestWatermarkNotFoundError:
    """Tests for WatermarkNotFoundError exception."""
    
    def test_creates_with_watermark_id(self):
        """Test exception is created with correct attributes."""
        exc = WatermarkNotFoundError("watermark-789")
        
        assert exc.error_code == "WATERMARK_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "watermark-789" in exc.message
        assert exc.watermark_id == "watermark-789"


class TestJobNotFoundError:
    """Tests for JobNotFoundError exception."""
    
    def test_creates_with_job_id(self):
        """Test exception is created with correct attributes."""
        exc = JobNotFoundError("job-abc")
        
        assert exc.error_code == "JOB_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "job-abc" in exc.message
        assert exc.job_id == "job-abc"


class TestCaptionNotFoundError:
    """Tests for CaptionNotFoundError exception."""
    
    def test_creates_with_video_id(self):
        """Test exception is created with correct attributes."""
        exc = CaptionNotFoundError("video-xyz")
        
        assert exc.error_code == "CAPTION_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "video-xyz" in exc.message
        assert exc.video_id == "video-xyz"


class TestInvalidFormatError:
    """Tests for InvalidFormatError exception."""
    
    def test_creates_with_message(self):
        """Test exception is created with correct attributes."""
        exc = InvalidFormatError("Unsupported video format")
        
        assert exc.error_code == "INVALID_FORMAT"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.message == "Unsupported video format"
    
    def test_with_format_details(self):
        """Test exception with format details."""
        exc = InvalidFormatError(
            "Unsupported video format",
            provided_format="wmv",
            supported_formats=["mp4", "mov", "avi"],
        )
        
        assert exc.details["provided_format"] == "wmv"
        assert exc.details["supported_formats"] == ["mp4", "mov", "avi"]


class TestInvalidParameterError:
    """Tests for InvalidParameterError exception."""
    
    def test_creates_with_message(self):
        """Test exception is created with correct attributes."""
        exc = InvalidParameterError("Invalid opacity value")
        
        assert exc.error_code == "INVALID_PARAMETER"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_with_parameter_details(self):
        """Test exception with parameter details."""
        exc = InvalidParameterError(
            "Invalid position value",
            parameter_name="position",
            provided_value="middle",
            allowed_values=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        )
        
        assert exc.details["parameter"] == "position"
        assert exc.details["provided_value"] == "middle"
        assert "top-left" in exc.details["allowed_values"]


class TestProcessingErrors:
    """Tests for processing-related exceptions."""
    
    def test_audio_extraction_error(self):
        """Test AudioExtractionError exception."""
        exc = AudioExtractionError()
        
        assert exc.error_code == "AUDIO_EXTRACTION_FAILED"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_audio_extraction_error_custom_message(self):
        """Test AudioExtractionError with custom message."""
        exc = AudioExtractionError("No audio stream found in video")
        
        assert exc.message == "No audio stream found in video"
    
    def test_transcription_error(self):
        """Test TranscriptionError exception."""
        exc = TranscriptionError()
        
        assert exc.error_code == "TRANSCRIPTION_FAILED"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_ffmpeg_error(self):
        """Test FFmpegError exception."""
        exc = FFmpegError()
        
        assert exc.error_code == "FFMPEG_ERROR"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_ffmpeg_error_with_details(self):
        """Test FFmpegError with details."""
        exc = FFmpegError("Encoding failed", details={"exit_code": 1})
        
        assert exc.message == "Encoding failed"
        assert exc.details["exit_code"] == 1


class TestInternalError:
    """Tests for InternalError exception."""
    
    def test_creates_with_defaults(self):
        """Test exception is created with default message."""
        exc = InternalError()
        
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "unexpected" in exc.message.lower()
    
    def test_with_log_message(self):
        """Test exception with log message for debugging."""
        exc = InternalError(
            message="An error occurred",
            log_message="Database connection failed: timeout after 30s",
        )
        
        assert exc.message == "An error occurred"
        assert exc.log_message == "Database connection failed: timeout after 30s"


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError exception."""
    
    def test_creates_with_service_name(self):
        """Test exception is created with service name."""
        exc = ServiceUnavailableError("Redis")
        
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Redis" in exc.message
        assert exc.details["service"] == "Redis"
        assert exc.service_name == "Redis"
    
    def test_with_custom_message(self):
        """Test exception with custom message."""
        exc = ServiceUnavailableError(
            "FFmpeg",
            message="FFmpeg binary not found in PATH",
        )
        
        assert exc.message == "FFmpeg binary not found in PATH"


# ============================================================================
# Test Exception Handlers
# ============================================================================

class TestAPIExceptionHandler:
    """Tests for the API exception handler."""
    
    def test_handles_video_not_found(self, test_app, client):
        """Test handler returns correct response for VideoNotFoundError."""
        @test_app.get("/test-video-not-found")
        async def raise_video_not_found():
            raise VideoNotFoundError("test-123")
        
        response = client.get("/test-video-not-found")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "VIDEO_NOT_FOUND"
        assert "test-123" in data["message"]
        assert "details" in data
    
    def test_handles_invalid_format(self, test_app, client):
        """Test handler returns correct response for InvalidFormatError."""
        @test_app.get("/test-invalid-format")
        async def raise_invalid_format():
            raise InvalidFormatError(
                "Unsupported format",
                provided_format="wmv",
                supported_formats=["mp4", "mov", "avi"],
            )
        
        response = client.get("/test-invalid-format")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_FORMAT"
        assert data["details"]["provided_format"] == "wmv"
    
    def test_handles_internal_error(self, test_app, client):
        """Test handler returns correct response for InternalError."""
        @test_app.get("/test-internal-error")
        async def raise_internal_error():
            raise InternalError(log_message="Sensitive database error details")
        
        response = client.get("/test-internal-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_ERROR"
        # Ensure sensitive details are not exposed
        assert "database" not in data["message"].lower()
    
    def test_handles_service_unavailable(self, test_app, client):
        """Test handler returns correct response for ServiceUnavailableError."""
        @test_app.get("/test-service-unavailable")
        async def raise_service_unavailable():
            raise ServiceUnavailableError("Redis")
        
        response = client.get("/test-service-unavailable")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"


class TestValidationExceptionHandler:
    """Tests for the validation exception handler."""
    
    def test_handles_validation_error(self, test_app, client):
        """Test handler returns field-level validation errors."""
        class TestRequest(BaseModel):
            opacity: float = Field(..., ge=0.0, le=1.0)
            name: str = Field(..., min_length=1)
        
        @test_app.post("/test-validation")
        async def validate_request(request: TestRequest):
            return {"status": "ok"}
        
        # Send invalid data
        response = client.post(
            "/test-validation",
            json={"opacity": 2.0, "name": ""},
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["message"] == "Request validation failed"
        assert isinstance(data["details"], list)
        assert len(data["details"]) >= 1
        
        # Check field-level errors are present
        field_names = [err["field"] for err in data["details"]]
        assert any("opacity" in field for field in field_names)


class TestGenericExceptionHandler:
    """Tests for the generic exception handler."""
    
    def test_handles_unexpected_exception(self, test_app, client):
        """Test handler returns generic error for unexpected exceptions."""
        @test_app.get("/test-unexpected")
        async def raise_unexpected():
            raise RuntimeError("Unexpected database connection error with credentials")
        
        response = client.get("/test-unexpected")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_ERROR"
        # Ensure internal details are not exposed
        assert "database" not in data["message"].lower()
        assert "credentials" not in data["message"].lower()
        assert data["details"] is None
    
    def test_handles_value_error(self, test_app, client):
        """Test handler catches ValueError and returns generic error."""
        @test_app.get("/test-value-error")
        async def raise_value_error():
            raise ValueError("Invalid internal state")
        
        response = client.get("/test-value-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_ERROR"


# ============================================================================
# Test Error Response Structure
# ============================================================================

class TestErrorResponseStructure:
    """Tests for consistent error response structure."""
    
    def test_all_responses_have_required_fields(self, test_app, client):
        """Test all error responses contain error_code, message, and details."""
        @test_app.get("/test-404")
        async def raise_404():
            raise VideoNotFoundError("vid-1")
        
        @test_app.get("/test-400")
        async def raise_400():
            raise InvalidFormatError("Bad format")
        
        @test_app.get("/test-500")
        async def raise_500():
            raise InternalError()
        
        for endpoint in ["/test-404", "/test-400", "/test-500"]:
            response = client.get(endpoint)
            data = response.json()
            
            assert "error_code" in data, f"Missing error_code in {endpoint}"
            assert "message" in data, f"Missing message in {endpoint}"
            assert "details" in data, f"Missing details in {endpoint}"
            
            # Verify types
            assert isinstance(data["error_code"], str)
            assert isinstance(data["message"], str)
            assert data["details"] is None or isinstance(data["details"], (dict, list))
