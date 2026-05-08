"""
Video processor service for the Video Caption Watermark API.

This module provides functionality for burning captions into videos
and combining caption burning with watermark application. All output
is in MP4 format.

Validates: Requirements 5.1, 5.2, 5.3, 5.4
"""

import os
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Optional

import ffmpeg

from app.models.enums import WatermarkPosition
from app.services.watermark_applicator import (
    validate_png_format,
    validate_opacity,
    DEFAULT_POSITION,
    DEFAULT_OPACITY,
    _get_overlay_position,
)


class VideoProcessingError(Exception):
    """Raised when video processing fails."""
    pass


# Output format is always MP4
OUTPUT_FORMAT = "mp4"
OUTPUT_CODEC = "libx264"
AUDIO_CODEC = "aac"


def burn_captions(
    video_path: str,
    caption_path: str,
    output_path: str
) -> str:
    """
    Burn captions into a video using FFmpeg subtitles filter.
    
    Args:
        video_path: Path to the source video file
        caption_path: Path to the caption file (SRT or VTT)
        output_path: Path for the output video file
        
    Returns:
        Path to the output video file
        
    Raises:
        VideoProcessingError: If processing fails
        
    Validates: Requirements 5.1
    """
    # Validate inputs
    if not os.path.exists(video_path):
        raise VideoProcessingError(f"Video file not found: {video_path}")
    
    if not os.path.exists(caption_path):
        raise VideoProcessingError(f"Caption file not found: {caption_path}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Ensure output has .mp4 extension
    if not output_path.lower().endswith('.mp4'):
        output_path = str(Path(output_path).with_suffix('.mp4'))
    
    try:
        # Build FFmpeg command with subtitles filter
        video = ffmpeg.input(video_path)

        # Apply subtitles filter
        video_with_subs = video.video.filter('subtitles', filename=caption_path)
        
        # Output to MP4
        output = ffmpeg.output(
            video_with_subs,
            video.audio,
            output_path,
            vcodec=OUTPUT_CODEC,
            acodec=AUDIO_CODEC,
            preset='medium'
        )
        
        # Run FFmpeg
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        if not os.path.exists(output_path):
            raise VideoProcessingError("FFmpeg produced no output file")
        
        return output_path
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise VideoProcessingError(f"Failed to burn captions: {stderr}")


def process_video(
    video_path: str,
    output_path: str,
    caption_path: Optional[str] = None,
    watermark_path: Optional[str] = None,
    watermark_position: WatermarkPosition = DEFAULT_POSITION,
    watermark_opacity: float = DEFAULT_OPACITY,
    watermark_scale: float = 1.0,
    watermark_padding: int = 10,
    caption_start_sec: float = 0.0,
    watermark_start_sec: float = 0.0,
) -> str:
    """
    Process video with captions and/or watermark in a single operation.
    
    This is the main entry point for combined video processing. It can:
    - Burn captions only
    - Apply watermark only
    - Apply both captions and watermark
    
    Output is always in MP4 format.
    
    Args:
        video_path: Path to the source video file
        output_path: Path for the output video file
        caption_path: Optional path to caption file (SRT or VTT)
        watermark_path: Optional path to watermark image (PNG)
        watermark_position: Watermark position (default: bottom-right)
        watermark_opacity: Watermark opacity 0.0-1.0 (default: 0.5)
        
    Returns:
        Path to the output video file
        
    Raises:
        VideoProcessingError: If processing fails
        
    Validates: Requirements 5.2, 5.3, 5.4
    """
    # Validate inputs
    if not os.path.exists(video_path):
        raise VideoProcessingError(f"Video file not found: {video_path}")
    
    if caption_path and not os.path.exists(caption_path):
        raise VideoProcessingError(f"Caption file not found: {caption_path}")
    
    if watermark_path:
        if not os.path.exists(watermark_path):
            raise VideoProcessingError(f"Watermark file not found: {watermark_path}")
        if not validate_png_format(watermark_path):
            raise VideoProcessingError("Watermark must be a PNG file")
        if not validate_opacity(watermark_opacity):
            raise VideoProcessingError("Opacity must be between 0.0 and 1.0")
        if watermark_scale <= 0:
            raise VideoProcessingError("Watermark scale must be greater than 0")
        if watermark_padding < 0:
            raise VideoProcessingError("Watermark padding must be >= 0")

    if caption_start_sec < 0:
        raise VideoProcessingError("caption_start_sec must be >= 0")

    if watermark_start_sec < 0:
        raise VideoProcessingError("watermark_start_sec must be >= 0")
    
    # At least one processing option must be specified
    if not caption_path and not watermark_path:
        raise VideoProcessingError(
            "At least one of caption_path or watermark_path must be provided"
        )
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Ensure output has .mp4 extension
    if not output_path.lower().endswith('.mp4'):
        output_path = str(Path(output_path).with_suffix('.mp4'))
    
    try:
        # Build FFmpeg filter graph
        video = ffmpeg.input(video_path)
        video_stream = video.video
        audio_stream = video.audio

        # Apply captions if provided
        if caption_path:
            video_stream = video_stream.filter('subtitles', filename=caption_path)
        
        # Apply watermark if provided
        if watermark_path:
            watermark = ffmpeg.input(watermark_path)

            if watermark_scale != 1.0:
                try:
                    probe = ffmpeg.probe(video_path)
                    video_meta_stream = next(s for s in probe.get('streams', []) if s.get('codec_type') == 'video')
                    video_width = int(video_meta_stream.get('width', 0))
                except Exception as e:
                    raise VideoProcessingError(f"Failed to read video dimensions for watermark scale: {e}")

                if video_width <= 0:
                    raise VideoProcessingError("Invalid video width for watermark scaling")

                target_w = max(1, int(video_width * watermark_scale))
                watermark = watermark.filter('scale', target_w, -1)
            
            # Apply opacity to watermark
            watermark_with_opacity = watermark.filter(
                'format', 'rgba'
            ).filter(
                'colorchannelmixer',
                aa=watermark_opacity
            )
            
            # Get position expression
            pos_expr = _get_overlay_position(watermark_position, padding=watermark_padding)
            
            # Overlay watermark
            video_stream = ffmpeg.overlay(
                video_stream,
                watermark_with_opacity,
                x=pos_expr.split(':')[0],
                y=pos_expr.split(':')[1],
                enable=f"gte(t,{watermark_start_sec})",
            )
        
        # Output to MP4
        output = ffmpeg.output(
            video_stream,
            audio_stream,
            output_path,
            vcodec=OUTPUT_CODEC,
            acodec=AUDIO_CODEC,
            preset='medium'
        )
        
        # Run FFmpeg
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        if not os.path.exists(output_path):
            raise VideoProcessingError("FFmpeg produced no output file")
        
        return output_path
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise VideoProcessingError(f"Failed to process video: {stderr}")


def merge_videos(
    cover_video_path: str,
    main_video_path: str,
    output_path: str,
    re_encode: bool = True,
) -> str:
    """
    Merge a cover video with a main course video.
    
    The cover video is placed before the main video. This function can work in two modes:
    - re_encode=True: Re-encodes both videos for guaranteed compatibility (safer)
    - re_encode=False: Uses concat demuxer (faster, but videos must be compatible)
    
    Args:
        cover_video_path: Path to the cover/intro video file
        main_video_path: Path to the main course video file
        output_path: Path for the merged output video file
        re_encode: If True, re-encode for compatibility (default: True)
        
    Returns:
        Path to the merged output video file
        
    Raises:
        VideoProcessingError: If merging fails
        
    Validates: Requirements 5.1, 5.4
    """
    # Validate inputs
    if not os.path.exists(cover_video_path):
        raise VideoProcessingError(f"Cover video not found: {cover_video_path}")
    
    if not os.path.exists(main_video_path):
        raise VideoProcessingError(f"Main video not found: {main_video_path}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Ensure output has .mp4 extension
    if not output_path.lower().endswith('.mp4'):
        output_path = str(Path(output_path).with_suffix('.mp4'))
    
    try:
        if re_encode:
            # Safe approach: Re-encode both videos to ensure compatibility
            # This is slower but guarantees the merge works regardless of source video properties
            cover = ffmpeg.input(cover_video_path)
            main = ffmpeg.input(main_video_path)

            try:
                main_probe = ffmpeg.probe(main_video_path)
                main_video_stream = next(
                    stream
                    for stream in main_probe.get('streams', [])
                    if stream.get('codec_type') == 'video'
                )
            except Exception as exc:  # noqa: BLE001
                raise VideoProcessingError(f"Failed to read main video metadata: {exc}")

            try:
                target_width = int(main_video_stream.get('width', 0))
                target_height = int(main_video_stream.get('height', 0))
            except (TypeError, ValueError) as exc:
                raise VideoProcessingError(f"Invalid main video dimensions: {exc}")

            if target_width <= 0 or target_height <= 0:
                raise VideoProcessingError("Invalid main video dimensions")

            main_fps_raw = str(main_video_stream.get('r_frame_rate', '30/1'))
            try:
                main_fps = float(Fraction(main_fps_raw))
            except (ZeroDivisionError, ValueError) as exc:
                raise VideoProcessingError(f"Invalid main video frame rate: {exc}")

            if main_fps <= 0:
                raise VideoProcessingError("Invalid main video frame rate")

            main_sar_raw = str(main_video_stream.get('sample_aspect_ratio', '1:1'))
            target_sar = '1/1' if main_sar_raw in {'0:1', 'N/A', ''} else main_sar_raw.replace(':', '/')

            # Standardize both inputs to same codec/resolution/fps/SAR
            cover_processed = (
                cover
                .video.filter('scale', target_width, target_height)
                .filter('fps', fps=main_fps_raw)
                .filter('setsar', sar=target_sar)
            )
            cover_audio = cover.audio

            main_processed = (
                main
                .video.filter('scale', target_width, target_height)
                .filter('fps', fps=main_fps_raw)
                .filter('setsar', sar=target_sar)
            )
            main_audio = main.audio

            # Concatenate using concat filter
            v_concat = ffmpeg.concat(cover_processed, main_processed, v=1, a=0)
            a_concat = ffmpeg.concat(cover_audio, main_audio, v=0, a=1)

            output = ffmpeg.output(
                v_concat,
                a_concat,
                output_path,
                vcodec=OUTPUT_CODEC,
                acodec=AUDIO_CODEC,
                preset='medium',
                crf=18,
            )
        else:
            # Fast approach: Use concat demuxer (videos must be compatible)
            # Create a temporary concat file listing
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            concat_file_path = concat_file.name
            try:
                concat_file.write(f"file '{os.path.abspath(cover_video_path)}'\n")
                concat_file.write(f"file '{os.path.abspath(main_video_path)}'\n")
                concat_file.close()

                # Use concat demuxer
                concat = ffmpeg.input(concat_file_path, format='concat', safe=0)
                output = ffmpeg.output(
                    concat,
                    output_path,
                    c='copy',  # Copy without re-encoding for speed
                )

                ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            finally:
                # Clean up temp file
                if os.path.exists(concat_file_path):
                    os.remove(concat_file_path)

            if not os.path.exists(output_path):
                raise VideoProcessingError("FFmpeg produced no output file")

            return output_path

        # Run FFmpeg
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        if not os.path.exists(output_path):
            raise VideoProcessingError("FFmpeg produced no output file")
        
        return output_path
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise VideoProcessingError(f"Failed to merge videos: {stderr}")


def get_output_format() -> str:
    """
    Get the output format for processed videos.
    
    Returns:
        Output format string (always "mp4")
        
    Validates: Requirements 5.4
    """
    return OUTPUT_FORMAT
