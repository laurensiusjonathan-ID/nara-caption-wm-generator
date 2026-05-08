"""Data models and schemas package."""

from app.models.enums import CaptionFormat, WatermarkPosition, JobStatus
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

__all__ = [
    # Enums
    "CaptionFormat",
    "WatermarkPosition",
    "JobStatus",
    # Video models
    "VideoUploadResponse",
    "VideoMetadata",
    # Caption models
    "CaptionGenerateRequest",
    "CaptionSegment",
    "CaptionResponse",
    "CaptionUpdateRequest",
    # Watermark models
    "WatermarkUploadResponse",
    "WatermarkMetadata",
    # Processing models
    "ProcessVideoRequest",
    # Job models
    "JobResponse",
    "JobListResponse",
    # Error models
    "ErrorResponse",
    "ValidationErrorResponse",
]
