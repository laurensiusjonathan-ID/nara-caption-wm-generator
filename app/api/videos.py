"""
Video management API endpoints for the Video Caption Watermark API.

This module provides endpoints for video upload, metadata retrieval,
and video deletion with cascade file cleanup.

Endpoints:
- POST /api/v1/videos/upload - Upload video with format validation
- GET /api/v1/videos/{video_id} - Get video metadata
- DELETE /api/v1/videos/{video_id} - Delete video and associated files

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.3
"""

from datetime import datetime
from typing import Dict, Any
import os

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.models.schemas import VideoUploadResponse, VideoMetadata, ErrorResponse
from app.services.video_service import (
    validate_video_format,
    extract_video_metadata,
    get_supported_formats,
    VideoValidationError,
    VideoProcessingError,
)
from app.storage.file_storage import LocalFileStorage
from app.config import settings
from app.models.enums import CaptionFormat


router = APIRouter()

# Initialize file storage
file_storage = LocalFileStorage(base_path=str(settings.storage_base_path))

# In-memory video metadata store (in production, use a database)
# Maps video_id to video metadata dict
video_metadata_store: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/videos/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid video format"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Upload a video file",
    description="Upload a video file for processing. Supported formats: MP4, MOV, AVI.",
)
async def upload_video(
    file: UploadFile = File(..., description="Video file to upload")
) -> VideoUploadResponse:
    """
    Upload a video file with format validation.
    
    Accepts video files in MP4, MOV, or AVI format. The file is stored
    with a unique identifier and metadata is extracted using FFmpeg.
    
    Args:
        file: The video file to upload
        
    Returns:
        VideoUploadResponse with video_id and extracted metadata
        
    Raises:
        HTTPException 400: If the video format is not supported
        HTTPException 500: If video processing fails
        
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    # Validate file format by extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": "Filename is required",
                "details": None,
            },
        )
    
    if not validate_video_format(file.filename):
        supported = get_supported_formats()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": f"Unsupported video format. Supported formats: {', '.join(supported).upper()}",
                "details": {
                    "provided_format": os.path.splitext(file.filename)[1].lower().lstrip('.'),
                    "supported_formats": supported,
                },
            },
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Save file to storage
        stored_filename = file_storage.save_upload(file_content, file.filename)
        
        # Extract video_id from stored filename (UUID part without extension)
        video_id = os.path.splitext(stored_filename)[0]
        
        # Get full path for metadata extraction
        file_path = file_storage.get_file_path(stored_filename, "upload")
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to store video file",
                    "details": None,
                },
            )
        
        # Extract video metadata
        metadata = extract_video_metadata(file_path)
        
        # Store metadata in memory
        created_at = datetime.utcnow()
        video_metadata_store[video_id] = {
            "video_id": video_id,
            "filename": file.filename,
            "stored_filename": stored_filename,
            "duration_seconds": metadata.duration_seconds,
            "resolution": metadata.resolution,
            "file_size_bytes": metadata.file_size_bytes,
            "has_captions": False,
            "has_output": False,
            "created_at": created_at,
        }
        
        return VideoUploadResponse(
            video_id=video_id,
            filename=file.filename,
            duration_seconds=metadata.duration_seconds,
            resolution=metadata.resolution,
            file_size_bytes=metadata.file_size_bytes,
            created_at=created_at,
        )
        
    except VideoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": str(e),
                "details": None,
            },
        )
    except VideoProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "FFMPEG_ERROR",
                "message": f"Failed to process video: {str(e)}",
                "details": None,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": None,
            },
        )


@router.get(
    "/videos/{video_id}",
    response_model=VideoMetadata,
    responses={
        404: {"model": ErrorResponse, "description": "Video not found"},
    },
    summary="Get video metadata",
    description="Retrieve metadata for a previously uploaded video.",
)
async def get_video(video_id: str) -> VideoMetadata:
    """
    Get metadata for a video by its ID.
    
    Returns the video metadata including duration, resolution, file size,
    and processing status flags.
    
    Args:
        video_id: Unique identifier of the video
        
    Returns:
        VideoMetadata with complete video information
        
    Raises:
        HTTPException 404: If the video is not found
        
    Validates: Requirements 1.5, 1.6
    """
    # Check if video exists in metadata store
    if video_id not in video_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "VIDEO_NOT_FOUND",
                "message": f"Video with ID '{video_id}' not found",
                "details": None,
            },
        )
    
    video_data = video_metadata_store[video_id]
    
    # Check if captions exist
    has_captions = False
    for fmt in CaptionFormat:
        caption_filename = f"{video_id}.{fmt.value}"
        if file_storage.get_file_path(caption_filename, "caption"):
            has_captions = True
            break
    
    # Check if output exists
    output_filename = f"{video_id}.mp4"
    has_output = file_storage.get_file_path(output_filename, "output") is not None
    
    return VideoMetadata(
        video_id=video_data["video_id"],
        filename=video_data["filename"],
        duration_seconds=video_data["duration_seconds"],
        resolution=video_data["resolution"],
        file_size_bytes=video_data["file_size_bytes"],
        has_captions=has_captions,
        has_output=has_output,
        created_at=video_data["created_at"],
    )


@router.delete(
    "/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Video not found"},
    },
    summary="Delete a video",
    description="Delete a video and all associated files (captions, processed outputs).",
)
async def delete_video(video_id: str) -> None:
    """
    Delete a video and all associated files.
    
    Performs cascade deletion of the source video, any generated captions,
    and processed output videos.
    
    Args:
        video_id: Unique identifier of the video to delete
        
    Raises:
        HTTPException 404: If the video is not found
        
    Validates: Requirements 8.3
    """
    # Check if video exists in metadata store
    if video_id not in video_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "VIDEO_NOT_FOUND",
                "message": f"Video with ID '{video_id}' not found",
                "details": None,
            },
        )
    
    # Delete all associated files (cascade deletion)
    file_storage.delete_video_files(video_id)
    
    # Remove from metadata store
    del video_metadata_store[video_id]
    
    # Return 204 No Content (no response body)
    return None
