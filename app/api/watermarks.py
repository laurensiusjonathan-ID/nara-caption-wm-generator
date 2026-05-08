"""
Watermark management API endpoints for the Video Caption Watermark API.

This module provides endpoints for watermark image upload, metadata retrieval,
and watermark deletion.

Endpoints:
- POST /api/v1/watermarks/upload - Upload watermark image (PNG only)
- GET /api/v1/watermarks/{watermark_id} - Get watermark metadata
- DELETE /api/v1/watermarks/{watermark_id} - Delete watermark

Validates: Requirements 4.1, 4.2
"""

from datetime import datetime
from typing import Dict, Any
import os

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.models.schemas import WatermarkUploadResponse, WatermarkMetadata, ErrorResponse
from app.services.watermark_applicator import (
    validate_png_format,
    validate_watermark_file,
    WatermarkValidationError,
)
from app.storage.file_storage import LocalFileStorage
from app.config import settings


router = APIRouter()

# Initialize file storage
file_storage = LocalFileStorage(base_path=str(settings.storage_base_path))

# In-memory watermark metadata store (in production, use a database)
# Maps watermark_id to watermark metadata dict
watermark_metadata_store: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/watermarks/upload",
    response_model=WatermarkUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid watermark format (non-PNG)"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Upload a watermark image",
    description="Upload a PNG watermark image for use in video processing. Only PNG format is supported.",
)
async def upload_watermark(
    file: UploadFile = File(..., description="PNG watermark image to upload")
) -> WatermarkUploadResponse:
    """
    Upload a watermark image with format validation.
    
    Accepts only PNG image files with transparency support. The file is stored
    with a unique identifier and metadata is extracted.
    
    Args:
        file: The PNG watermark image to upload
        
    Returns:
        WatermarkUploadResponse with watermark_id and image dimensions
        
    Raises:
        HTTPException 400: If the file is not a PNG image
        HTTPException 500: If watermark processing fails
        
    Validates: Requirements 4.1, 4.2
    """
    # Validate filename is provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": "Filename is required",
                "details": None,
            },
        )
    
    # Validate file format by extension
    if not validate_png_format(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": "Invalid watermark format. Only PNG files are supported.",
                "details": {
                    "provided_format": os.path.splitext(file.filename)[1].lower().lstrip('.'),
                    "supported_formats": ["png"],
                },
            },
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Save file to storage
        stored_filename = file_storage.save_watermark(file_content, file.filename)
        
        # Extract watermark_id from stored filename (UUID part without extension)
        watermark_id = os.path.splitext(stored_filename)[0]
        
        # Get full path for metadata extraction
        file_path = file_storage.get_file_path(stored_filename, "watermark")
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to store watermark file",
                    "details": None,
                },
            )
        
        # Validate watermark file and extract metadata
        watermark_meta = validate_watermark_file(file_path)
        
        # Store metadata in memory
        created_at = datetime.utcnow()
        watermark_metadata_store[watermark_id] = {
            "watermark_id": watermark_id,
            "filename": file.filename,
            "stored_filename": stored_filename,
            "width": watermark_meta.width,
            "height": watermark_meta.height,
            "created_at": created_at,
        }
        
        return WatermarkUploadResponse(
            watermark_id=watermark_id,
            filename=file.filename,
            width=watermark_meta.width,
            height=watermark_meta.height,
            created_at=created_at,
        )
        
    except WatermarkValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FORMAT",
                "message": str(e),
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
    "/watermarks/{watermark_id}",
    response_model=WatermarkMetadata,
    responses={
        404: {"model": ErrorResponse, "description": "Watermark not found"},
    },
    summary="Get watermark metadata",
    description="Retrieve metadata for a previously uploaded watermark image.",
)
async def get_watermark(watermark_id: str) -> WatermarkMetadata:
    """
    Get metadata for a watermark by its ID.
    
    Returns the watermark metadata including filename, dimensions,
    and upload timestamp.
    
    Args:
        watermark_id: Unique identifier of the watermark
        
    Returns:
        WatermarkMetadata with complete watermark information
        
    Raises:
        HTTPException 404: If the watermark is not found
        
    Validates: Requirements 4.1
    """
    # Check if watermark exists in metadata store
    if watermark_id not in watermark_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WATERMARK_NOT_FOUND",
                "message": f"Watermark with ID '{watermark_id}' not found",
                "details": None,
            },
        )
    
    watermark_data = watermark_metadata_store[watermark_id]
    
    return WatermarkMetadata(
        watermark_id=watermark_data["watermark_id"],
        filename=watermark_data["filename"],
        width=watermark_data["width"],
        height=watermark_data["height"],
        created_at=watermark_data["created_at"],
    )


@router.delete(
    "/watermarks/{watermark_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Watermark not found"},
    },
    summary="Delete a watermark",
    description="Delete a watermark image from the system.",
)
async def delete_watermark(watermark_id: str) -> None:
    """
    Delete a watermark by its ID.
    
    Removes the watermark image file from storage and its metadata.
    
    Args:
        watermark_id: Unique identifier of the watermark to delete
        
    Raises:
        HTTPException 404: If the watermark is not found
        
    Validates: Requirements 4.1
    """
    # Check if watermark exists in metadata store
    if watermark_id not in watermark_metadata_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "WATERMARK_NOT_FOUND",
                "message": f"Watermark with ID '{watermark_id}' not found",
                "details": None,
            },
        )
    
    # Get stored filename for deletion
    watermark_data = watermark_metadata_store[watermark_id]
    stored_filename = watermark_data["stored_filename"]
    
    # Delete watermark file from storage
    file_path = file_storage.get_file_path(stored_filename, "watermark")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove from metadata store
    del watermark_metadata_store[watermark_id]
    
    # Return 204 No Content (no response body)
    return None
