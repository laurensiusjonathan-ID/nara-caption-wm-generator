"""
Caption management API endpoints for the Video Caption Watermark API.

This module provides endpoints for caption generation, retrieval, and editing.
Caption generation is processed asynchronously via Celery background tasks.

Endpoints:
- POST /api/v1/videos/{video_id}/captions/generate - Start caption generation job
- GET /api/v1/videos/{video_id}/captions - Get generated captions
- PUT /api/v1/videos/{video_id}/captions - Update/edit captions

Validates: Requirements 2.6, 2.7, 3.1, 3.2, 3.3, 3.4
"""

from typing import Optional
import os

from fastapi import APIRouter, HTTPException, status, Query

from app.models.schemas import (
    CaptionGenerateRequest,
    CaptionResponse,
    CaptionUpdateRequest,
    CaptionSegment,
    JobResponse,
    ErrorResponse,
)
from app.models.enums import CaptionFormat, JobStatus
from app.services.caption_formatter import (
    parse_srt,
    parse_vtt,
    format_to_srt,
    format_to_vtt,
    CaptionFormatError,
    CaptionSegment as FormatterCaptionSegment,
    validate_timestamps,
    TimestampValidationError,
)
from app.services.job_manager import RedisJobManager
from app.storage.file_storage import LocalFileStorage
from app.tasks.video_tasks import generate_captions_task
from app.config import settings

# Import video_metadata_store from videos module to check video existence
from app.api.videos import video_metadata_store


router = APIRouter()

# Initialize services
file_storage = LocalFileStorage(base_path=str(settings.storage_base_path))
job_manager = RedisJobManager()


@router.post(
    "/videos/{video_id}/captions/generate",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"model": ErrorResponse, "description": "Video not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Start caption generation",
    description="Start an asynchronous caption generation job for a video. "
                "Returns a job ID that can be used to track progress.",
)
async def generate_captions(
    video_id: str,
    request: CaptionGenerateRequest = CaptionGenerateRequest(),
) -> JobResponse:
    """
    Start caption generation job for a video.
    
    Initiates an asynchronous caption generation process using faster-whisper
    for speech-to-text transcription. The job runs in the background and
    can be tracked using the returned job ID.
    
    Args:
        video_id: Unique identifier of the video
        request: Caption generation options (language, output format)
        
    Returns:
        JobResponse with job_id and initial status
        
    Raises:
        HTTPException 404: If the video is not found
        HTTPException 500: If job creation fails
        
    Validates: Requirements 2.6, 2.7
    """
    # Check if video exists
    if video_id not in video_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "VIDEO_NOT_FOUND",
                "message": f"Video with ID '{video_id}' not found",
                "details": None,
            },
        )
    
    # Get video metadata
    video_data = video_metadata_store[video_id]
    stored_filename = video_data.get("stored_filename")
    
    # Get video file path
    video_path = file_storage.get_file_path(stored_filename, "upload")
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Video file not found in storage",
                "details": None,
            },
        )
    
    try:
        # Create job
        job_id = job_manager.create_job(
            job_type="caption_generation",
            video_id=video_id
        )
        
        # Determine output path for captions
        caption_filename = f"{video_id}.{request.output_format.value}"
        caption_path = os.path.join(
            str(settings.storage_base_path),
            "captions",
            caption_filename
        )
        
        # Queue the background task
        generate_captions_task.delay(
            job_id=job_id,
            video_id=video_id,
            video_path=video_path,
            output_path=caption_path,
            language=request.language,
            output_format=request.output_format.value,
        )
        
        # Get job details for response
        job_data = job_manager.get_job(job_id)
        
        return JobResponse(
            job_id=job_data["job_id"],
            job_type=job_data["job_type"],
            video_id=job_data["video_id"],
            status=job_data["status"],
            progress=job_data.get("progress"),
            result_path=job_data.get("result_path"),
            error_message=job_data.get("error_message"),
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to create caption generation job: {str(e)}",
                "details": None,
            },
        )


@router.get(
    "/videos/{video_id}/captions",
    response_model=CaptionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Video or captions not found"},
        400: {"model": ErrorResponse, "description": "Invalid format requested"},
    },
    summary="Get generated captions",
    description="Retrieve generated captions for a video in the requested format (SRT or VTT).",
)
async def get_captions(
    video_id: str,
    format: Optional[CaptionFormat] = Query(
        default=CaptionFormat.SRT,
        description="Caption format to return (srt or vtt)"
    ),
) -> CaptionResponse:
    """
    Get generated captions for a video.
    
    Returns the caption content in the requested format. If captions were
    generated in a different format, they will be converted automatically.
    
    Args:
        video_id: Unique identifier of the video
        format: Desired caption format (SRT or VTT, defaults to SRT)
        
    Returns:
        CaptionResponse with caption content and parsed segments
        
    Raises:
        HTTPException 404: If the video or captions are not found
        
    Validates: Requirements 2.6, 3.1, 3.2
    """
    # Check if video exists
    if video_id not in video_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "VIDEO_NOT_FOUND",
                "message": f"Video with ID '{video_id}' not found",
                "details": None,
            },
        )
    
    # Try to find caption file in requested format first
    caption_filename = f"{video_id}.{format.value}"
    caption_path = file_storage.get_file_path(caption_filename, "caption")
    
    # If not found in requested format, try the other format
    source_format = format
    if not caption_path:
        other_format = CaptionFormat.VTT if format == CaptionFormat.SRT else CaptionFormat.SRT
        other_filename = f"{video_id}.{other_format.value}"
        caption_path = file_storage.get_file_path(other_filename, "caption")
        if caption_path:
            source_format = other_format
    
    # If still not found, captions don't exist
    if not caption_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CAPTION_NOT_FOUND",
                "message": f"Captions not found for video '{video_id}'. "
                          "Generate captions first using POST /api/v1/videos/{video_id}/captions/generate",
                "details": None,
            },
        )
    
    try:
        # Read caption content
        with open(caption_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse segments from source format
        if source_format == CaptionFormat.SRT:
            segments_data = parse_srt(content)
        else:
            segments_data = parse_vtt(content)
        
        # Convert to requested format if different
        if source_format != format:
            if format == CaptionFormat.SRT:
                content = format_to_srt(segments_data)
            else:
                content = format_to_vtt(segments_data)
        
        # Convert to CaptionSegment models
        segments = [
            CaptionSegment(
                index=i + 1,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"]
            )
            for i, seg in enumerate(segments_data)
        ]
        
        return CaptionResponse(
            video_id=video_id,
            format=format,
            content=content,
            segments=segments,
        )
        
    except CaptionFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to parse caption file: {str(e)}",
                "details": None,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to read captions: {str(e)}",
                "details": None,
            },
        )


@router.put(
    "/videos/{video_id}/captions",
    response_model=CaptionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Video not found"},
        400: {"model": ErrorResponse, "description": "Invalid caption format"},
    },
    summary="Update/edit captions",
    description="Update or edit captions for a video. The caption content must be valid SRT or VTT format.",
)
async def update_captions(
    video_id: str,
    request: CaptionUpdateRequest,
) -> CaptionResponse:
    """
    Update or edit captions for a video.
    
    Allows users to submit edited caption content after reviewing
    auto-generated captions. The content is validated for format
    compliance before being stored.
    
    Args:
        video_id: Unique identifier of the video
        request: Caption update request with format and content
        
    Returns:
        CaptionResponse with updated caption content and parsed segments
        
    Raises:
        HTTPException 404: If the video is not found
        HTTPException 400: If the caption format is invalid
        
    Validates: Requirements 3.3, 3.4
    """
    # Check if video exists
    if video_id not in video_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "VIDEO_NOT_FOUND",
                "message": f"Video with ID '{video_id}' not found",
                "details": None,
            },
        )
    
    # Validate and parse caption content
    try:
        if request.format == CaptionFormat.SRT:
            segments_data = parse_srt(request.content)
        else:
            segments_data = parse_vtt(request.content)
        
        # Validate timestamps (start < end, chronological order, no overlaps)
        caption_segments = [
            FormatterCaptionSegment(start=s['start'], end=s['end'], text=s['text'])
            for s in segments_data
        ]
        validate_timestamps(caption_segments)
        
    except CaptionFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": f"Invalid caption format: {str(e)}",
                "details": {
                    "format": request.format.value,
                    "error": str(e),
                },
            },
        )
    except TimestampValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": f"Invalid caption timestamps: {str(e)}",
                "details": {
                    "format": request.format.value,
                    "error": str(e),
                },
            },
        )
    
    try:
        # Save the updated captions
        file_storage.save_caption(
            content=request.content,
            video_id=video_id,
            format=request.format
        )
        
        # Convert to CaptionSegment models
        segments = [
            CaptionSegment(
                index=i + 1,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"]
            )
            for i, seg in enumerate(segments_data)
        ]
        
        return CaptionResponse(
            video_id=video_id,
            format=request.format,
            content=request.content,
            segments=segments,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to save captions: {str(e)}",
                "details": None,
            },
        )
