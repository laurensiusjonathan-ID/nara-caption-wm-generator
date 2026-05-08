"""
Request and response models for the Video Caption Watermark API.

This module defines all Pydantic models used for API request validation
and response serialization. Models are organized by functional area:
video management, caption operations, watermark operations, processing,
job management, and error handling.

Validates: Requirements 1.4, 7.3, 7.4
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import CaptionFormat, WatermarkPosition, JobStatus


# ============================================================================
# Video Models
# ============================================================================

class VideoUploadResponse(BaseModel):
    """
    Response model for successful video upload.
    
    Returned when a video is successfully uploaded and stored.
    Contains the unique identifier and extracted metadata.
    
    Validates: Requirements 1.4
    """
    video_id: str = Field(..., description="Unique identifier for the uploaded video")
    filename: str = Field(..., description="Original filename of the uploaded video")
    duration_seconds: float = Field(..., description="Duration of the video in seconds", ge=0)
    resolution: str = Field(..., description="Video resolution (e.g., '1920x1080')")
    file_size_bytes: int = Field(..., description="Size of the video file in bytes", ge=0)
    created_at: datetime = Field(..., description="Timestamp when the video was uploaded")


class VideoMetadata(BaseModel):
    """
    Complete metadata for a video in the system.
    
    Includes upload information, processing status flags, and timestamps.
    Used for GET /api/v1/videos/{video_id} responses.
    
    Validates: Requirements 1.5
    """
    video_id: str = Field(..., description="Unique identifier for the video")
    filename: str = Field(..., description="Original filename of the video")
    duration_seconds: float = Field(..., description="Duration of the video in seconds", ge=0)
    resolution: str = Field(..., description="Video resolution (e.g., '1920x1080')")
    file_size_bytes: int = Field(..., description="Size of the video file in bytes", ge=0)
    has_captions: bool = Field(..., description="Whether captions have been generated for this video")
    has_output: bool = Field(..., description="Whether a processed output video exists")
    created_at: datetime = Field(..., description="Timestamp when the video was uploaded")


# ============================================================================
# Caption Models
# ============================================================================

class CaptionGenerateRequest(BaseModel):
    """
    Request model for caption generation.
    
    Specifies the language for transcription and desired output format.
    Defaults to Indonesian language and SRT format.
    
    Validates: Requirements 2.2, 2.4, 2.5, 2.6
    """
    language: str = Field(
        default="id",
        description="Language code for transcription (ISO 639-1 format, e.g., 'id' for Indonesian, 'en' for English)"
    )
    output_format: CaptionFormat = Field(
        default=CaptionFormat.SRT,
        description="Desired caption format (SRT or VTT)"
    )


class CaptionSegment(BaseModel):
    """
    A single caption segment with timing and text.
    
    Represents one caption entry with start time, end time, and text content.
    Used in caption responses and for validation.
    
    Validates: Requirements 2.3
    """
    index: int = Field(..., description="Sequential index of the caption segment (1-based)", ge=1)
    start_time: float = Field(..., description="Start time of the caption in seconds", ge=0)
    end_time: float = Field(..., description="End time of the caption in seconds", ge=0)
    text: str = Field(..., description="Caption text content", min_length=1)


class CaptionResponse(BaseModel):
    """
    Response model for caption retrieval.
    
    Contains the complete caption data including format, raw content,
    and parsed segments for programmatic access.
    
    Validates: Requirements 3.1, 3.2
    """
    video_id: str = Field(..., description="Video identifier these captions belong to")
    format: CaptionFormat = Field(..., description="Format of the caption content (SRT or VTT)")
    content: str = Field(..., description="Raw caption file content in the specified format")
    segments: List[CaptionSegment] = Field(..., description="Parsed caption segments for programmatic access")


class CaptionUpdateRequest(BaseModel):
    """
    Request model for updating/editing captions.
    
    Allows users to submit edited caption content after reviewing
    auto-generated captions. Content must be valid SRT or VTT format.
    
    Validates: Requirements 3.3, 3.4
    """
    format: CaptionFormat = Field(..., description="Format of the caption content being submitted")
    content: str = Field(..., description="Complete caption file content in the specified format", min_length=1)


# ============================================================================
# Watermark Models
# ============================================================================

class WatermarkUploadResponse(BaseModel):
    """
    Response model for successful watermark upload.
    
    Returned when a watermark image is successfully uploaded and stored.
    Contains the unique identifier and image dimensions.
    
    Validates: Requirements 4.1
    """
    watermark_id: str = Field(..., description="Unique identifier for the uploaded watermark")
    filename: str = Field(..., description="Original filename of the watermark image")
    width: int = Field(..., description="Width of the watermark image in pixels", ge=1)
    height: int = Field(..., description="Height of the watermark image in pixels", ge=1)
    created_at: datetime = Field(..., description="Timestamp when the watermark was uploaded")


class WatermarkMetadata(BaseModel):
    """
    Complete metadata for a watermark in the system.
    
    Used for GET /api/v1/watermarks/{watermark_id} responses.
    
    Validates: Requirements 4.1
    """
    watermark_id: str = Field(..., description="Unique identifier for the watermark")
    filename: str = Field(..., description="Original filename of the watermark image")
    width: int = Field(..., description="Width of the watermark image in pixels", ge=1)
    height: int = Field(..., description="Height of the watermark image in pixels", ge=1)
    created_at: datetime = Field(..., description="Timestamp when the watermark was uploaded")


# ============================================================================
# Processing Models
# ============================================================================

class ProcessVideoRequest(BaseModel):
    """
    Request model for video processing.
    
    Specifies which operations to apply (captions and/or watermark)
    and configuration for watermark application.
    
    Validates: Requirements 5.1, 5.2, 5.3, 4.4, 4.5, 4.6, 4.7
    """
    apply_captions: bool = Field(
        default=False,
        description="Whether to burn captions into the video"
    )
    apply_watermark: bool = Field(
        default=False,
        description="Whether to apply a watermark to the video"
    )
    watermark_id: Optional[str] = Field(
        default=None,
        description="Watermark identifier to use (required if apply_watermark is True)"
    )
    watermark_position: WatermarkPosition = Field(
        default=WatermarkPosition.BOTTOM_RIGHT,
        description="Position of the watermark on the video"
    )
    watermark_opacity: float = Field(
        default=0.5,
        description="Opacity of the watermark (0.0 = transparent, 1.0 = opaque)",
        ge=0.0,
        le=1.0
    )


class MergeVideosRequest(BaseModel):
    """
    Request model for merging videos.
    
    Merges a cover video with a main course video. The cover video is placed before the main video.
    
    Validates: Requirements 5.1, 5.4
    """
    cover_video_id: str = Field(
        ...,
        description="Video identifier for the cover/intro video"
    )
    main_video_id: str = Field(
        ...,
        description="Video identifier for the main course video"
    )
    re_encode: bool = Field(
        default=True,
        description="If True, re-encode for guaranteed compatibility (slower but safer)"
    )


# ============================================================================
# Job Models
# ============================================================================

class JobResponse(BaseModel):
    """
    Response model for job status queries.
    
    Contains complete job information including status, progress,
    results, and error details if applicable.
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    job_id: str = Field(..., description="Unique identifier for the job")
    job_type: str = Field(..., description="Type of job (e.g., 'caption_generation', 'video_processing')")
    video_id: str = Field(..., description="Video identifier this job is processing")
    status: JobStatus = Field(..., description="Current status of the job")
    progress: Optional[int] = Field(
        default=None,
        description="Progress percentage (0-100) if available",
        ge=0,
        le=100
    )
    result_path: Optional[str] = Field(
        default=None,
        description="Path to the result file (present when status is 'completed')"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message (present when status is 'failed')"
    )
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    updated_at: datetime = Field(..., description="Timestamp when the job was last updated")


class JobListResponse(BaseModel):
    """
    Response model for job listing.
    
    Contains a list of all jobs and the total count.
    
    Validates: Requirements 6.6
    """
    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs", ge=0)


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    Used for all error responses to provide consistent error structure
    with error code, message, and optional details.
    
    Validates: Requirements 7.3
    """
    error_code: str = Field(..., description="Machine-readable error code (e.g., 'VIDEO_NOT_FOUND')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details (e.g., validation errors, context information)"
    )


class ValidationErrorResponse(BaseModel):
    """
    Validation error response model.
    
    Used specifically for request validation failures (422 responses).
    Provides field-level error details.
    
    Validates: Requirements 7.4
    """
    error_code: str = Field(
        default="VALIDATION_ERROR",
        description="Error code for validation failures"
    )
    message: str = Field(
        default="Request validation failed",
        description="General validation error message"
    )
    details: List[dict] = Field(
        ...,
        description="List of field-level validation errors with field names and error messages"
    )
