"""
Video service for the Video Caption Watermark API.

This module provides functionality for video metadata extraction and format validation
using ffmpeg-python. It handles video file analysis and validation against supported formats.

Validates: Requirements 1.2, 1.4
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import ffmpeg


class VideoValidationError(Exception):
    """Raised when video validation fails."""
    pass


class VideoProcessingError(Exception):
    """Raised when video processing operations fail."""
    pass


@dataclass
class VideoMetadata:
    """
    Video metadata extracted from file.
    
    Attributes:
        duration_seconds: Video duration in seconds
        width: Video width in pixels
        height: Video height in pixels
        file_size_bytes: File size in bytes
        codec: Video codec name
        format_name: Container format name
    """
    duration_seconds: float
    width: int
    height: int
    file_size_bytes: int
    codec: Optional[str] = None
    format_name: Optional[str] = None
    
    @property
    def resolution(self) -> str:
        """Return resolution as WxH string."""
        return f"{self.width}x{self.height}"


# Supported video formats (case-insensitive)
SUPPORTED_VIDEO_FORMATS = {"mp4", "mov", "avi"}


def validate_video_format(filename: str) -> bool:
    """
    Validate that a video file has a supported format based on extension.
    
    Supported formats: MP4, MOV, AVI (case-insensitive)
    
    Args:
        filename: Name or path of the video file
        
    Returns:
        True if format is supported, False otherwise
        
    Validates: Requirements 1.2
    """
    if not filename:
        return False
    
    # Extract extension and normalize to lowercase
    ext = Path(filename).suffix.lower().lstrip('.')
    return ext in SUPPORTED_VIDEO_FORMATS


def get_supported_formats() -> list[str]:
    """
    Get list of supported video formats.
    
    Returns:
        List of supported format extensions
    """
    return list(SUPPORTED_VIDEO_FORMATS)


def extract_video_metadata(video_path: str) -> VideoMetadata:
    """
    Extract metadata from a video file using ffmpeg-python.
    
    Extracts duration, resolution (width/height), file size, codec, and format.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        VideoMetadata object with extracted information
        
    Raises:
        VideoValidationError: If file doesn't exist or is not a valid video
        VideoProcessingError: If ffmpeg fails to probe the file
        
    Validates: Requirements 1.4
    """
    # Check file exists
    if not os.path.exists(video_path):
        raise VideoValidationError(f"Video file not found: {video_path}")
    
    # Get file size
    file_size = os.path.getsize(video_path)
    
    try:
        # Probe video file with ffmpeg
        probe = ffmpeg.probe(video_path)
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise VideoProcessingError(f"Failed to probe video file: {stderr}")
    
    # Extract format information
    format_info = probe.get('format', {})
    duration = float(format_info.get('duration', 0))
    format_name = format_info.get('format_name', '')
    
    # Find video stream
    video_stream = None
    for stream in probe.get('streams', []):
        if stream.get('codec_type') == 'video':
            video_stream = stream
            break
    
    if not video_stream:
        raise VideoValidationError("No video stream found in file")
    
    # Extract video stream properties
    width = video_stream.get('width', 0)
    height = video_stream.get('height', 0)
    codec = video_stream.get('codec_name', '')
    
    if width == 0 or height == 0:
        raise VideoValidationError("Invalid video dimensions")
    
    return VideoMetadata(
        duration_seconds=duration,
        width=width,
        height=height,
        file_size_bytes=file_size,
        codec=codec,
        format_name=format_name
    )


def validate_video_file(video_path: str) -> VideoMetadata:
    """
    Validate a video file and extract its metadata.
    
    Performs both format validation (by extension) and content validation
    (by probing with ffmpeg).
    
    Args:
        video_path: Path to the video file
        
    Returns:
        VideoMetadata object if validation passes
        
    Raises:
        VideoValidationError: If format is unsupported or file is invalid
        VideoProcessingError: If ffmpeg fails to process the file
        
    Validates: Requirements 1.2, 1.4
    """
    # Validate format by extension
    if not validate_video_format(video_path):
        ext = Path(video_path).suffix.lower().lstrip('.')
        raise VideoValidationError(
            f"Unsupported video format: {ext}. "
            f"Supported formats: {', '.join(SUPPORTED_VIDEO_FORMATS)}"
        )
    
    # Extract and validate metadata
    return extract_video_metadata(video_path)
