"""
Watermark applicator service for the Video Caption Watermark API.

This module provides functionality for validating PNG watermark images
and applying them to videos using FFmpeg overlay filters with configurable
positioning and opacity.

Validates: Requirements 4.1, 4.3, 4.4, 4.6
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import ffmpeg

from app.models.enums import WatermarkPosition


class WatermarkValidationError(Exception):
    """Raised when watermark validation fails."""
    pass


class WatermarkApplicationError(Exception):
    """Raised when watermark application fails."""
    pass


@dataclass
class WatermarkMetadata:
    """
    Watermark image metadata.
    
    Attributes:
        width: Image width in pixels
        height: Image height in pixels
        has_alpha: Whether the image has an alpha channel
    """
    width: int
    height: int
    has_alpha: bool = True


# Valid opacity range
MIN_OPACITY = 0.0
MAX_OPACITY = 1.0
DEFAULT_OPACITY = 0.5
DEFAULT_POSITION = WatermarkPosition.BOTTOM_RIGHT


def validate_png_format(filename: str) -> bool:
    """
    Validate that a file has PNG extension.
    
    Args:
        filename: Name or path of the file
        
    Returns:
        True if file has .png extension (case-insensitive)
        
    Validates: Requirements 4.1
    """
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower()
    return ext == '.png'


def validate_opacity(opacity: float) -> bool:
    """
    Validate that opacity is within valid range [0.0, 1.0].
    
    Args:
        opacity: Opacity value to validate
        
    Returns:
        True if opacity is valid
        
    Validates: Requirements 4.6
    """
    return MIN_OPACITY <= opacity <= MAX_OPACITY


def validate_watermark_position(position: str) -> bool:
    """
    Validate that position is a valid WatermarkPosition value.
    
    Args:
        position: Position string to validate
        
    Returns:
        True if position is valid
        
    Validates: Requirements 4.4
    """
    valid_positions = {p.value for p in WatermarkPosition}
    return position in valid_positions


def validate_watermark_file(watermark_path: str) -> WatermarkMetadata:
    """
    Validate a watermark file is a valid PNG image.
    
    Uses ffprobe to verify the file is a valid image and extract metadata.
    
    Args:
        watermark_path: Path to the watermark image file
        
    Returns:
        WatermarkMetadata with image dimensions
        
    Raises:
        WatermarkValidationError: If file is not a valid PNG
        
    Validates: Requirements 4.1
    """
    if not os.path.exists(watermark_path):
        raise WatermarkValidationError(f"Watermark file not found: {watermark_path}")
    
    if not validate_png_format(watermark_path):
        raise WatermarkValidationError(
            "Invalid watermark format. Only PNG files are supported."
        )
    
    try:
        # Probe the image file
        probe = ffmpeg.probe(watermark_path)
        
        # Find image stream
        image_stream = None
        for stream in probe.get('streams', []):
            if stream.get('codec_type') == 'video':
                image_stream = stream
                break
        
        if not image_stream:
            raise WatermarkValidationError("No valid image data found in file")
        
        width = image_stream.get('width', 0)
        height = image_stream.get('height', 0)
        
        if width == 0 or height == 0:
            raise WatermarkValidationError("Invalid image dimensions")
        
        # Check for PNG codec
        codec = image_stream.get('codec_name', '').lower()
        if codec != 'png':
            raise WatermarkValidationError(
                f"Invalid image format: {codec}. Only PNG is supported."
            )
        
        return WatermarkMetadata(
            width=width,
            height=height,
            has_alpha=True  # PNG supports alpha
        )
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise WatermarkValidationError(f"Failed to validate watermark: {stderr}")


def _get_overlay_position(
    position: WatermarkPosition,
    padding: int = 10
) -> str:
    """
    Get FFmpeg overlay filter position expression.
    
    Args:
        position: Watermark position enum value
        padding: Padding from edges in pixels
        
    Returns:
        FFmpeg overlay position expression string
    """
    positions = {
        WatermarkPosition.TOP_LEFT: f"{padding}:{padding}",
        WatermarkPosition.TOP_RIGHT: f"W-w-{padding}:{padding}",
        WatermarkPosition.BOTTOM_LEFT: f"{padding}:H-h-{padding}",
        WatermarkPosition.BOTTOM_RIGHT: f"W-w-{padding}:H-h-{padding}",
        WatermarkPosition.CENTER: "(W-w)/2:(H-h)/2",
    }
    return positions.get(position, positions[WatermarkPosition.BOTTOM_RIGHT])


def apply_watermark(
    video_path: str,
    watermark_path: str,
    output_path: str,
    position: WatermarkPosition = DEFAULT_POSITION,
    opacity: float = DEFAULT_OPACITY
) -> str:
    """
    Apply a watermark to a video using FFmpeg overlay filter.
    
    Args:
        video_path: Path to the source video file
        watermark_path: Path to the PNG watermark image
        output_path: Path for the output video file
        position: Watermark position (default: bottom-right)
        opacity: Watermark opacity 0.0-1.0 (default: 0.5)
        
    Returns:
        Path to the output video file
        
    Raises:
        WatermarkValidationError: If inputs are invalid
        WatermarkApplicationError: If FFmpeg processing fails
        
    Validates: Requirements 4.3, 4.4, 4.6
    """
    # Validate inputs
    if not os.path.exists(video_path):
        raise WatermarkValidationError(f"Video file not found: {video_path}")
    
    if not os.path.exists(watermark_path):
        raise WatermarkValidationError(f"Watermark file not found: {watermark_path}")
    
    if not validate_png_format(watermark_path):
        raise WatermarkValidationError("Watermark must be a PNG file")
    
    if not validate_opacity(opacity):
        raise WatermarkValidationError(
            f"Opacity must be between {MIN_OPACITY} and {MAX_OPACITY}"
        )
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Get position expression
        pos_expr = _get_overlay_position(position)
        
        # Build FFmpeg filter graph
        video = ffmpeg.input(video_path)
        watermark = ffmpeg.input(watermark_path)
        
        # Apply opacity to watermark using colorchannelmixer
        # format=rgba ensures alpha channel is preserved
        watermark_with_opacity = watermark.filter(
            'format', 'rgba'
        ).filter(
            'colorchannelmixer',
            aa=opacity  # Multiply alpha channel by opacity
        )
        
        # Overlay watermark on video
        output = ffmpeg.overlay(
            video,
            watermark_with_opacity,
            x=pos_expr.split(':')[0],
            y=pos_expr.split(':')[1]
        )
        
        # Output to MP4
        output = ffmpeg.output(
            output,
            video.audio,  # Preserve audio
            output_path,
            vcodec='libx264',
            acodec='aac',
            preset='medium'
        )
        
        # Run FFmpeg
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        if not os.path.exists(output_path):
            raise WatermarkApplicationError("FFmpeg produced no output file")
        
        return output_path
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise WatermarkApplicationError(f"Failed to apply watermark: {stderr}")
