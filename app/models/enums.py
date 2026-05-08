"""
Enum definitions for the Video Caption Watermark API.

This module defines the core enumerations used throughout the application
for caption formats, watermark positioning, and job status tracking.
"""

from enum import Enum


class CaptionFormat(str, Enum):
    """
    Supported caption file formats.
    
    Attributes:
        SRT: SubRip Subtitle format (.srt)
        VTT: WebVTT (Web Video Text Tracks) format (.vtt)
    
    Validates: Requirements 2.4, 2.5
    """
    SRT = "srt"
    VTT = "vtt"


class WatermarkPosition(str, Enum):
    """
    Supported watermark overlay positions on video.
    
    Attributes:
        TOP_LEFT: Position watermark in the top-left corner
        TOP_RIGHT: Position watermark in the top-right corner
        BOTTOM_LEFT: Position watermark in the bottom-left corner
        BOTTOM_RIGHT: Position watermark in the bottom-right corner (default)
        CENTER: Position watermark in the center of the video
    
    Validates: Requirements 4.4
    """
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"


class JobStatus(str, Enum):
    """
    Job lifecycle status values.
    
    Status transitions follow the pattern:
    pending -> processing -> (completed | failed)
    
    Attributes:
        PENDING: Job created but not yet started
        PROCESSING: Job is currently being executed
        COMPLETED: Job finished successfully
        FAILED: Job encountered an error and could not complete
    
    Validates: Requirements 6.1
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
