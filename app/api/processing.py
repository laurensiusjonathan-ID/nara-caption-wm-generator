"""
Video processing API endpoints for the Video Caption Watermark API.

This module provides endpoints for starting video processing jobs and
downloading processed video outputs. Processing is handled asynchronously
via Celery background tasks.

Endpoints:
- POST /api/v1/videos/{video_id}/process - Start video processing job
- GET /api/v1/videos/{video_id}/output - Download processed video

Validates: Requirements 4.5, 4.7, 5.3, 5.5, 5.6
"""

import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.models.schemas import ProcessVideoRequest, JobResponse, ErrorResponse
from app.models.enums import CaptionFormat
from app.services.job_manager import RedisJobManager
from app.storage.file_storage import LocalFileStorage
from app.tasks.video_tasks import process_video_task
from app.config import settings

# Import metadata stores from other API modules
from app.api.videos import video_metadata_store
from app.api.watermarks import watermark_metadata_store


router = APIRouter()

# Initialize services
file_storage = LocalFileStorage(base_path=str(settings.storage_base_path))
job_manager = RedisJobManager()


@router.post(
    "/videos/{video_id}/process",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "Video or watermark not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Start video processing",
    description="Start an asynchronous video processing job to apply captions and/or watermark. "
                "Returns a job ID that can be used to track progress.",
)
async def process_video(
    video_id: str,
    request: ProcessVideoRequest = ProcessVideoRequest(),
) -> JobResponse:
    """
    Start video processing job for a video.
    
    Initiates an asynchronous video processing operation that can apply
    captions and/or watermark to the video. The job runs in the background
    and can be tracked using the returned job ID.
    
    Args:
        video_id: Unique identifier of the video
        request: Processing options (apply_captions, apply_watermark, watermark settings)
        
    Returns:
        JobResponse with job_id and initial status
        
    Raises:
        HTTPException 400: If invalid parameters are provided
        HTTPException 404: If the video or watermark is not found
        HTTPException 500: If job creation fails
        
    Validates: Requirements 4.5, 4.7, 5.3
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
    
    # Validate that at least one operation is requested
    if not request.apply_captions and not request.apply_watermark:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_PARAMETER",
                "message": "At least one of apply_captions or apply_watermark must be True",
                "details": {
                    "apply_captions": request.apply_captions,
                    "apply_watermark": request.apply_watermark,
                },
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
    
    # Handle caption path if applying captions
    caption_path = None
    if request.apply_captions:
        # Try to find caption file (SRT first, then VTT)
        for fmt in CaptionFormat:
            caption_filename = f"{video_id}.{fmt.value}"
            found_path = file_storage.get_file_path(caption_filename, "caption")
            if found_path:
                caption_path = found_path
                break
        
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
    
    # Handle watermark path if applying watermark
    watermark_path = None
    if request.apply_watermark:
        # Validate watermark_id is provided
        if not request.watermark_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PARAMETER",
                    "message": "watermark_id is required when apply_watermark is True",
                    "details": None,
                },
            )
        
        # Check if watermark exists
        if request.watermark_id not in watermark_metadata_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "WATERMARK_NOT_FOUND",
                    "message": f"Watermark with ID '{request.watermark_id}' not found",
                    "details": None,
                },
            )
        
        # Get watermark file path
        watermark_data = watermark_metadata_store[request.watermark_id]
        watermark_stored_filename = watermark_data.get("stored_filename")
        watermark_path = file_storage.get_file_path(watermark_stored_filename, "watermark")
        
        if not watermark_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Watermark file not found in storage",
                    "details": None,
                },
            )
    
    try:
        # Create job
        job_id = job_manager.create_job(
            job_type="video_processing",
            video_id=video_id
        )
        
        # Determine output path for processed video
        output_path = os.path.join(
            str(settings.storage_base_path),
            "outputs",
            f"{video_id}.mp4"
        )
        
        # Queue the background task
        process_video_task.delay(
            job_id=job_id,
            video_id=video_id,
            video_path=video_path,
            output_path=output_path,
            caption_path=caption_path,
            watermark_path=watermark_path,
            watermark_position=request.watermark_position.value if request.apply_watermark else None,
            watermark_opacity=request.watermark_opacity if request.apply_watermark else None,
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
                "message": f"Failed to create video processing job: {str(e)}",
                "details": None,
            },
        )


@router.get(
    "/videos/{video_id}/output",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Processed video file",
            "content": {"video/mp4": {}},
        },
        404: {"model": ErrorResponse, "description": "Video or output not found"},
    },
    summary="Download processed video",
    description="Download the processed video file for a video that has been processed.",
)
async def download_output(video_id: str) -> FileResponse:
    """
    Download processed video output.
    
    Returns the processed video file for download. The video must have
    been processed successfully before this endpoint can be used.
    
    Args:
        video_id: Unique identifier of the video
        
    Returns:
        FileResponse with the processed video file
        
    Raises:
        HTTPException 404: If the video or output is not found
        
    Validates: Requirements 5.5, 5.6
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
    
    # Check if output exists
    output_filename = f"{video_id}.mp4"
    output_path = file_storage.get_file_path(output_filename, "output")
    
    if not output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "OUTPUT_NOT_FOUND",
                "message": f"Processed output not found for video '{video_id}'. "
                          "Process the video first using POST /api/v1/videos/{video_id}/process",
                "details": None,
            },
        )
    
    # Get original filename for download
    video_data = video_metadata_store[video_id]
    original_filename = video_data.get("filename", "output.mp4")
    
    # Create download filename based on original
    base_name = os.path.splitext(original_filename)[0]
    download_filename = f"{base_name}_processed.mp4"
    
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=download_filename,
    )
