"""
Unit tests for request/response schema models.

Tests verify that Pydantic models correctly validate input data,
apply default values, and enforce constraints.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.schemas import (
    VideoUploadResponse,
    VideoMetadata,
    CaptionGenerateRequest,
    CaptionSegment,
    CaptionResponse,
    CaptionUpdateRequest,
    WatermarkUploadResponse,
    WatermarkMetadata,
    ProcessVideoRequest,
    JobResponse,
    JobListResponse,
    ErrorResponse,
    ValidationErrorResponse,
)
from app.models.enums import CaptionFormat, WatermarkPosition, JobStatus


class TestVideoModels:
    """Tests for video-related schema models."""

    def test_video_upload_response_valid(self):
        """Test VideoUploadResponse with valid data."""
        now = datetime.now()
        response = VideoUploadResponse(
            video_id="vid_123",
            filename="test.mp4",
            duration_seconds=120.5,
            resolution="1920x1080",
            file_size_bytes=1024000,
            created_at=now
        )
        assert response.video_id == "vid_123"
        assert response.filename == "test.mp4"
        assert response.duration_seconds == 120.5
        assert response.resolution == "1920x1080"
        assert response.file_size_bytes == 1024000
        assert response.created_at == now

    def test_video_upload_response_negative_duration(self):
        """Test VideoUploadResponse rejects negative duration."""
        with pytest.raises(ValidationError) as exc_info:
            VideoUploadResponse(
                video_id="vid_123",
                filename="test.mp4",
                duration_seconds=-10.0,
                resolution="1920x1080",
                file_size_bytes=1024000,
                created_at=datetime.now()
            )
        assert "duration_seconds" in str(exc_info.value)

    def test_video_metadata_valid(self):
        """Test VideoMetadata with valid data."""
        now = datetime.now()
        metadata = VideoMetadata(
            video_id="vid_123",
            filename="test.mp4",
            duration_seconds=120.5,
            resolution="1920x1080",
            file_size_bytes=1024000,
            has_captions=True,
            has_output=False,
            created_at=now
        )
        assert metadata.has_captions is True
        assert metadata.has_output is False


class TestCaptionModels:
    """Tests for caption-related schema models."""

    def test_caption_generate_request_defaults(self):
        """Test CaptionGenerateRequest applies default values."""
        request = CaptionGenerateRequest()
        assert request.language == "id"
        assert request.output_format == CaptionFormat.SRT

    def test_caption_generate_request_custom_values(self):
        """Test CaptionGenerateRequest with custom values."""
        request = CaptionGenerateRequest(
            language="en",
            output_format=CaptionFormat.VTT
        )
        assert request.language == "en"
        assert request.output_format == CaptionFormat.VTT

    def test_caption_segment_valid(self):
        """Test CaptionSegment with valid data."""
        segment = CaptionSegment(
            index=1,
            start_time=0.0,
            end_time=2.5,
            text="Hello world"
        )
        assert segment.index == 1
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5
        assert segment.text == "Hello world"

    def test_caption_segment_invalid_index(self):
        """Test CaptionSegment rejects zero or negative index."""
        with pytest.raises(ValidationError) as exc_info:
            CaptionSegment(
                index=0,
                start_time=0.0,
                end_time=2.5,
                text="Hello"
            )
        assert "index" in str(exc_info.value)

    def test_caption_segment_empty_text(self):
        """Test CaptionSegment rejects empty text."""
        with pytest.raises(ValidationError) as exc_info:
            CaptionSegment(
                index=1,
                start_time=0.0,
                end_time=2.5,
                text=""
            )
        assert "text" in str(exc_info.value)

    def test_caption_response_valid(self):
        """Test CaptionResponse with valid data."""
        segments = [
            CaptionSegment(index=1, start_time=0.0, end_time=2.5, text="First"),
            CaptionSegment(index=2, start_time=2.5, end_time=5.0, text="Second")
        ]
        response = CaptionResponse(
            video_id="vid_123",
            format=CaptionFormat.SRT,
            content="1\n00:00:00,000 --> 00:00:02,500\nFirst\n\n",
            segments=segments
        )
        assert response.video_id == "vid_123"
        assert response.format == CaptionFormat.SRT
        assert len(response.segments) == 2

    def test_caption_update_request_valid(self):
        """Test CaptionUpdateRequest with valid data."""
        request = CaptionUpdateRequest(
            format=CaptionFormat.VTT,
            content="WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHello"
        )
        assert request.format == CaptionFormat.VTT
        assert "WEBVTT" in request.content


class TestWatermarkModels:
    """Tests for watermark-related schema models."""

    def test_watermark_upload_response_valid(self):
        """Test WatermarkUploadResponse with valid data."""
        now = datetime.now()
        response = WatermarkUploadResponse(
            watermark_id="wm_123",
            filename="logo.png",
            width=200,
            height=100,
            created_at=now
        )
        assert response.watermark_id == "wm_123"
        assert response.width == 200
        assert response.height == 100

    def test_watermark_upload_response_invalid_dimensions(self):
        """Test WatermarkUploadResponse rejects zero or negative dimensions."""
        with pytest.raises(ValidationError) as exc_info:
            WatermarkUploadResponse(
                watermark_id="wm_123",
                filename="logo.png",
                width=0,
                height=100,
                created_at=datetime.now()
            )
        assert "width" in str(exc_info.value)


class TestProcessingModels:
    """Tests for video processing schema models."""

    def test_process_video_request_defaults(self):
        """Test ProcessVideoRequest applies default values."""
        request = ProcessVideoRequest()
        assert request.apply_captions is False
        assert request.apply_watermark is False
        assert request.watermark_id is None
        assert request.watermark_position == WatermarkPosition.BOTTOM_RIGHT
        assert request.watermark_opacity == 0.5

    def test_process_video_request_custom_values(self):
        """Test ProcessVideoRequest with custom values."""
        request = ProcessVideoRequest(
            apply_captions=True,
            apply_watermark=True,
            watermark_id="wm_123",
            watermark_position=WatermarkPosition.TOP_LEFT,
            watermark_opacity=0.8
        )
        assert request.apply_captions is True
        assert request.apply_watermark is True
        assert request.watermark_id == "wm_123"
        assert request.watermark_position == WatermarkPosition.TOP_LEFT
        assert request.watermark_opacity == 0.8

    def test_process_video_request_opacity_validation(self):
        """Test ProcessVideoRequest validates opacity range."""
        # Valid opacity values
        ProcessVideoRequest(watermark_opacity=0.0)
        ProcessVideoRequest(watermark_opacity=0.5)
        ProcessVideoRequest(watermark_opacity=1.0)
        
        # Invalid opacity values
        with pytest.raises(ValidationError):
            ProcessVideoRequest(watermark_opacity=-0.1)
        
        with pytest.raises(ValidationError):
            ProcessVideoRequest(watermark_opacity=1.1)


class TestJobModels:
    """Tests for job management schema models."""

    def test_job_response_valid(self):
        """Test JobResponse with valid data."""
        now = datetime.now()
        response = JobResponse(
            job_id="job_123",
            job_type="caption_generation",
            video_id="vid_123",
            status=JobStatus.PROCESSING,
            progress=50,
            result_path=None,
            error_message=None,
            created_at=now,
            updated_at=now
        )
        assert response.job_id == "job_123"
        assert response.status == JobStatus.PROCESSING
        assert response.progress == 50

    def test_job_response_completed_with_result(self):
        """Test JobResponse for completed job with result."""
        now = datetime.now()
        response = JobResponse(
            job_id="job_123",
            job_type="video_processing",
            video_id="vid_123",
            status=JobStatus.COMPLETED,
            progress=100,
            result_path="/outputs/vid_123_processed.mp4",
            error_message=None,
            created_at=now,
            updated_at=now
        )
        assert response.status == JobStatus.COMPLETED
        assert response.result_path is not None
        assert response.error_message is None

    def test_job_response_failed_with_error(self):
        """Test JobResponse for failed job with error message."""
        now = datetime.now()
        response = JobResponse(
            job_id="job_123",
            job_type="caption_generation",
            video_id="vid_123",
            status=JobStatus.FAILED,
            progress=None,
            result_path=None,
            error_message="Audio extraction failed",
            created_at=now,
            updated_at=now
        )
        assert response.status == JobStatus.FAILED
        assert response.error_message is not None
        assert response.result_path is None

    def test_job_response_invalid_progress(self):
        """Test JobResponse validates progress range."""
        now = datetime.now()
        
        # Valid progress values
        JobResponse(
            job_id="job_123",
            job_type="test",
            video_id="vid_123",
            status=JobStatus.PROCESSING,
            progress=0,
            created_at=now,
            updated_at=now
        )
        
        JobResponse(
            job_id="job_123",
            job_type="test",
            video_id="vid_123",
            status=JobStatus.PROCESSING,
            progress=100,
            created_at=now,
            updated_at=now
        )
        
        # Invalid progress values
        with pytest.raises(ValidationError):
            JobResponse(
                job_id="job_123",
                job_type="test",
                video_id="vid_123",
                status=JobStatus.PROCESSING,
                progress=-1,
                created_at=now,
                updated_at=now
            )
        
        with pytest.raises(ValidationError):
            JobResponse(
                job_id="job_123",
                job_type="test",
                video_id="vid_123",
                status=JobStatus.PROCESSING,
                progress=101,
                created_at=now,
                updated_at=now
            )

    def test_job_list_response_valid(self):
        """Test JobListResponse with valid data."""
        now = datetime.now()
        jobs = [
            JobResponse(
                job_id="job_1",
                job_type="caption_generation",
                video_id="vid_1",
                status=JobStatus.COMPLETED,
                created_at=now,
                updated_at=now
            ),
            JobResponse(
                job_id="job_2",
                job_type="video_processing",
                video_id="vid_2",
                status=JobStatus.PROCESSING,
                created_at=now,
                updated_at=now
            )
        ]
        response = JobListResponse(jobs=jobs, total=2)
        assert len(response.jobs) == 2
        assert response.total == 2

    def test_job_list_response_empty(self):
        """Test JobListResponse with empty list."""
        response = JobListResponse(jobs=[], total=0)
        assert len(response.jobs) == 0
        assert response.total == 0


class TestErrorModels:
    """Tests for error response schema models."""

    def test_error_response_valid(self):
        """Test ErrorResponse with valid data."""
        response = ErrorResponse(
            error_code="VIDEO_NOT_FOUND",
            message="The requested video does not exist",
            details={"video_id": "vid_123"}
        )
        assert response.error_code == "VIDEO_NOT_FOUND"
        assert response.message == "The requested video does not exist"
        assert response.details["video_id"] == "vid_123"

    def test_error_response_without_details(self):
        """Test ErrorResponse without optional details."""
        response = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred"
        )
        assert response.error_code == "INTERNAL_ERROR"
        assert response.details is None

    def test_validation_error_response_valid(self):
        """Test ValidationErrorResponse with valid data."""
        response = ValidationErrorResponse(
            details=[
                {"field": "duration_seconds", "error": "must be greater than 0"},
                {"field": "filename", "error": "field required"}
            ]
        )
        assert response.error_code == "VALIDATION_ERROR"
        assert response.message == "Request validation failed"
        assert len(response.details) == 2

    def test_validation_error_response_custom_message(self):
        """Test ValidationErrorResponse with custom message."""
        response = ValidationErrorResponse(
            error_code="CUSTOM_VALIDATION",
            message="Custom validation message",
            details=[{"field": "test", "error": "invalid"}]
        )
        assert response.error_code == "CUSTOM_VALIDATION"
        assert response.message == "Custom validation message"
